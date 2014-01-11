'''
Madeira OpsAgent States worker object

@author: Thibault BRONCHAIN
'''


## IMPORTS
# System imports
import threading
import time
# Custom imports
from opsagent import utils
from opsagent.objects import send
from opsagent.exception import *
##

## DEFINES
# State succeed
SUCCESS=True
# State failed
FAIL=False
# Time to resend if failure
WAIT_RESEND=1
# Time before retrying state execution
WAIT_STATE_RETRY=1
##


## STATES WORKER OBJECT
# Manages the states execution
class StatesWorker(threading.Thread):
    def __init__(self, config):
        # init thread and object
        threading.Thread.__init__(self)
        self.__config = config
        self.__manager = None

        # events
        self.__cv = threading.Condition()
        self.__wait_event = threading.Event()

        # states variables
        self.__version = None
        self.__states = None
        self.__done = []
        self.__status = 0

        # flags
        self.__run = False
        self.__waiting = False

        # builtins map
        self.__builtins = {
            'Wait' : self.__exec_wait,
            }


    ## NETWORK RELAY
    # retry sending after disconnection
    def __send(self, data):
        utils.log("DEBUG", "Attempting to send data to backend ...",('__send',self))
        try:
            if not self.__manager:
                raise SWNoManagerException
            self.__manager.send_json(data)
        except Exception as e:
            utils.log("ERROR", "Can't send data '%s', reason: '%s'."%(data,e),('__send',self))
            if self.__run:
                utils.log("WARNING", "Still running, retrying in %s seconds.",('__send',self))
                time.sleep(WAIT_RESEND)
                self.__send(data)
            else:
                utils.log("WARNING", "Not running, aborting send.",('__send',self))
        else:
            utils.log("DEBUG", "Data successfully sent.",('__send',self))
    ##


    ## CONTROL METHODS
    # Switch manager
    def set_manager(self, manager):
        utils.log("DEBUG", "Setting new manager",('set_manager',self))
        self.__manager = manager

    # Return waiting state
    def is_waiting(self):
        utils.log("DEBUG", "Wait status: %s"%(self.__waiting),('is_waiting',self))
        return self.__waiting

    # Return version ID
    def get_version(self):
        utils.log("DEBUG", "Curent version: %s"%(self.__version),('get_version',self))
        return self.__version

    # Reset states status
    def reset(self):
        self.__status = 0
    ##


    ## KILL PROCESS
    # Kill child process
    def __kill_childs(self):
        # TODO
        pass

    # Halt wait
    def __kill_wait(self):
        utils.log("DEBUG", "killing wait status",('kill',self))
        self.__wait_event.set()

    # Kill the current execution
    def kill(self):
        if self.__run:
            if self.__waiting:
                self.__kill_wait()
            self.__kill_childs()
            utils.log("DEBUG", "Sending stop execution signal.",('kill',self))
            self.__run = False
            utils.log("INFO", "Execution killed.",('kill',self))
        else:
            utils.log("DEBUG", "Execution not running, nothing to do.",('kill',self))
    ##


    ## LOAD PROCESS
    # Load new recipe
    def load(self, version=None, states=None):
        utils.log("DEBUG", "Aquire conditional lock ...",('load',self))
        self.__cv.acquire()
        utils.log("DEBUG", "Conditional lock acquired.",('load',self))
        self.__version = version
        if states:
            utils.log("INFO", "Loading new states.",('load',self))
            self.__states = states
        else:
            utils.log("INFO", "No change in states.",('load',self))
        utils.log("DEBUG", "Reseting status.",('load',self))
        self.reset()
        utils.log("DEBUG", "Allow to run.",('load',self))
        self.__run = True
        utils.log("DEBUG", "Notify execution thread.",('load',self))
        self.__cv.notify()
        utils.log("DEBUG", "Release conditional lock.",('load',self))
        self.__cv.release()
    ##


    ## WAIT PROCESS
    # Add state to done list
    def state_done(self, id):
        utils.log("DEBUG", "Adding id '%s' to done states list."%(id),('state_done',self))
        self.__done.append(id)
        self.__wait_event.set()
    ##


    ## MAIN EXECUTION
    # Action on wait
    def __exec_wait(self, id, module, parameter):
        waited_s = parameter.get('stateid')
        waited_i = parameter.get('instance_id')
        if (not waited_s) or (not waited_i):
            raise SWWaitFormatException
        utils.log("INFO", "Waiting for state '%s' on instance '%s'..."%(waited_s,waited_i),('__exec_wait',self))
        self.__waiting = True
        while (id not in self.__done) and (self.__run):
            self.__wait_event.wait()
            self.__wait_event.clear()
            utils.log("INFO", "New state status received, analysing ...",('__exec_wait',self))
        self.__waiting = False
        if id in self.__done:
            value = SUCCESS
            utils.log("INFO", "Waited state completed.",('__exec_wait',self))
        else:
            value = FAIL
            utils.log("WARNING", "Waited state ABORTED.",('__exec_wait',self))
        return (value,None,None)

    # Call salt library
    def __exec_salt(self, id, module, parameter):
        utils.log("INFO", "Loading state ID '%s' from module '%s' ..."%(id,module),('__exec_salt',self))
        # TODO dict conversion + salt call
        time.sleep(5)
        # /TODO
        (result,err_log,out_log) = (SUCCESS,"ERR SALT","OUT SALT")
        utils.log("INFO", "State ID '%s' from module '%s' done, result '%s'."%(id,module,result),('__exec_salt',self))
        utils.log("DEBUG", "State out log='%s'"%(out_log),('__exec_salt',self))
        utils.log("DEBUG", "State error log='%s'"%(err_log),('__exec_salt',self))
        return (result,err_log,out_log)

    # Callback on start
    def run(self):
        utils.log("INFO", "Running StatesWorker ...",('run',self))
        utils.log("DEBUG", "Waiting for recipes ...",('run',self))
        self.__cv.acquire()
        while not self.__run:
            self.__cv.wait()
        utils.log("DEBUG", "Ready to go ...",('run',self))
        while self.__run:
            state = self.__states[self.__status]
            utils.log("INFO", "Running state '%s', #%s"%(state['stateid'], self.__status),('run',self))
            try:
                if state.get('module') in self.__builtins:
                    (result,err_log,out_log) = self.__builtins[state['module']](state['stateid'],
                                                                                state['module'],
                                                                                state['parameter'])
                else:
                    (result,err_log,out_log) = self.__exec_salt(state['stateid'],
                                                                state['module'],
                                                                state['parameter'])
            except SWWaitFormatException:
                utils.log("ERROR", "Wrong wait request",('run',self))
                result = FAIL
                err_log = "Wrong wait request"
                out_log = None
            except Exception as e:
                utils.log("ERROR", "Unknown exception: '%s'."%(e),('run',self))
                result = FAIL
                err_log = "Unknown exception: '%s'."%(e)
                out_log = None
            self.__waiting = False
            if self.__run:
                utils.log("INFO", "Execution complete, reporting logs to backend.",('run',self))
                self.__send(send.statelog(init=self.__config['init'],
                                          version=self.__version,
                                          id=state['stateid'],
                                          result=result,
                                          err_log=err_log,
                                          out_log=out_log))
                if result == SUCCESS:
                    # global status iteration
                    self.__status += 1
                    if self.__status >= len(self.__states):
                        self.__status = 0
                        utils.log("INFO", "All good, last state succeed! Back to first one.",('run',self))
                    else:
                        utils.log("INFO", "All good, switching to next state.",('run',self))
                else:
                    utils.log("WARNING", "Something went wrong, retrying current state in %s seconds"%(WAIT_STATE_RETRY),('run',self))
                    time.sleep(WAIT_STATE_RETRY)
            else:
                utils.log("WARNING", "Execution aborted.",('run',self))
        self.__cv.release()
        self.run()
    ##
##