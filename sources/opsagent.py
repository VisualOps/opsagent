#!/usr/bin/python
'''
VisualOps agent launcher script
(c) 2014 - MadeiraCloud LTD.

@author: Thibault BRONCHAIN
'''



# System imports
from optparse import OptionParser
import logging
import logging.handlers
import time
import sys
import signal
import os

# Custom imports
from opsagent.daemon import Daemon
from opsagent.config import Config
from opsagent import utils
from opsagent.exception import ConfigFileException
from opsagent.manager import Manager
from opsagent.state.worker import StateWorker


# general defines
USAGE='usage: %prog [-hqv] [-l logfile] [-c configfile] (start|stop|restart|stop-wait|restart-wait|stop-end|restart-end)'
VERSION_NBR='None'
VERSION='%prog '+VERSION_NBR
WAIT_RECONNECT=10


# logger settings
LOGLVL_VALUES=['DEBUG','INFO','WARNING','ERROR']
LOG_FORMAT = '[%(levelname)s]-%(asctime)s: %(message)s'
def __log(lvl, f=None):
    level = logging.getLevelName(lvl)
    formatter = logging.Formatter(LOG_FORMAT)
    handler = (logging.handlers.RotatingFileHandler(f,maxBytes=(1024*1024*10),backupCount=5) if f else logging.StreamHandler())
    logger = logging.getLogger()
    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)


# OpsAgent safe runner
class OpsAgentRunner(Daemon):
    def run_manager(self):
        utils.log("DEBUG", "Creating Network Manager ...",('run_manager','OpsAgentRunner'))
        manager = Manager(url=self.config['userdata']['ws_uri'], config=self.config, statesworker=self.sw)
        utils.log("DEBUG", "Network Manager created.",('run_manager','OpsAgentRunner'))
        try:
            utils.log("DEBUG", "Connecting manager to backend.",('run_manager','OpsAgentRunner'))
            manager.connect()
            utils.log("DEBUG", "Connection done, registering to StateWorker.",('run_manager','OpsAgentRunner'))
            self.sw.set_manager(manager)
            utils.log("DEBUG", "Registration done, running forever ...",('run_manager','OpsAgentRunner'))
            manager.run_forever()
            utils.log("DEBUG", "Network connection lost/aborted.",('run_manager','OpsAgentRunner'))
        except Exception as e:
            utils.log("ERROR", "Network error: '%s'"%(e),('run_manager','OpsAgentRunner'))
            if manager.connected():
                utils.log("INFO", "Connection not closed. Closing ...",('run_manager','OpsAgentRunner'))
                try:
                    manager.close()
                except Exception:
                    utils.log("DEBUG", "Can't close connection (already closed?).",('run_manager','OpsAgentRunner'))
                utils.log("DEBUG", "Connection closed.",('run_manager','OpsAgentRunner'))
            else:
                utils.log("DEBUG", "Connection already closed.",('run_manager','OpsAgentRunner'))
        self.sw.set_manager(None)
        del manager

    def run(self):
        # init
        self.sw = StateWorker(config=self.config)

        sw = self.sw
        haltfile = self.haltfile
        pidfile = self.pidfile

        # terminating process
        def handler(signum=None, frame=None):
            utils.log("WARNING", "Signal handler called with signal %s"%signum,('handler','OpsAgentRunner'))
            father = False
            try:
                fd = file(haltfile,'r')
                halt = fd.read().strip()
                fd.close()
                fd = file(pidfile,'r')
                if int(fd.read().strip()) == int(os.getpid()):
                    father = True
                fd.close()
            except IOError:
                halt = None
            except Exception as e:
                utils.log("WARNING", "Unexpected error, forcing quit: '%s'."%(e),('handler','OpsAgentRunner'))
                halt = None
            if halt == "wait":
                utils.log("WARNING", "Waiting current state end before end...",('handler','OpsAgentRunner'))
                sw.abort()
            elif halt == "end":
                utils.log("WARNING", "Waiting current recipe end before end...",('handler','OpsAgentRunner'))
                sw.abort(end=True)
            elif father:
                utils.log("WARNING", "Exiting now...",('handler','OpsAgentRunner'))
                sw.abort(kill=True)
            else:
                utils.log("WARNING", "Not main process, exiting.",('handler','OpsAgentRunner'))
                sys.exit(0)

        # handle termination
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
            try: signal.signal(sig, handler)
            except Exception: pass #pass some signals if not POSIX

        # start
        self.sw.start()

        # run forever
        while self.sw and not self.sw.aborted():
            try:
                # run manager
                self.run_manager()
            except Exception as e:
                utils.log("ERROR", "Unexpected error: '%s'"%(e),('run','OpsAgentRunner'))
                time.sleep(0.1)
                utils.log("WARNING", "Conenction aborted, retrying ...",('run','OpsAgentRunner'))
            if self.sw and (not self.sw.aborted()):
                time.sleep(WAIT_RECONNECT)

        # end properly
        if self.sw and self.sw.is_alive():
            self.sw.join()
        self.sw = None


# option parser
def optParse():
    parser = OptionParser(usage=USAGE, version=VERSION)
    parser.add_option("-c", "--config-file", action="store", dest="config_file",
                      help="specify config file"
                      )
    parser.add_option("-l", "--log-file", action="store", dest="log_file",
                      help="specify log file"
                      )
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False,
                      help="operate quietly (log minimal info)"
                      )
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="verbose mode (log debug -all- info)"
                      )
    parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False,
                      help="debug mode (display log)"
                      )
    return parser.parse_args()


def main():
    # options parsing
    options, args = optParse()

    # config parser
    try:
        config = Config(options.config_file).getConfig()
    except ConfigFileException:
        config = Config().getConfig()
    except Exception as e:
        sys.stderr.write("ERROR: Unknown fatal config exception: %s, loading default.\n"%(e))
        config = Config().getConfig()
    config['runtime']['config_path'] = options.config_file

    # set log level
    loglvl = config['global']['loglvl']
    if loglvl and loglvl not in LOGLVL_VALUES:
        sys.stderr.write("WARNING: Wrong loglvl '%s' (check config file). Loading in default mode (INFO).\n"%(loglvl))
        loglvl = 'INFO'
    if options.verbose: loglvl = 'DEBUG'
    elif options.quiet: loglvl = 'ERROR'
    logfile = (options.log_file if options.log_file else config['global'].get('logfile'))
    config['runtime']['loglvl'] = loglvl
    config['runtime']['logfile'] = (logfile if not options.debug else None)
    __log(config['runtime']['loglvl'],config['runtime']['logfile'])

    # run
    runner = OpsAgentRunner(config)
    command = sys.argv[-1]
    if command == "start":
        runner.start()
    elif command == "stop":
        runner.stop()
    elif command == "restart":
        runner.restart()
    elif command == "stop-wait":
        runner.stop(wait=True)
    elif command == "restart-wait":
        runner.restart(wait=True)
    elif command == "stop-end":
        runner.stop(end=True)
    elif command == "restart-end":
        runner.restart(end=True)
    elif command == "status":
        runner.status()
    else:
        runner.run()



if __name__ == '__main__':
    main()
