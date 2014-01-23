#!/bin/bash
##
## @author: Thibault BRONCHAIN
## (c) 2014 MadeiraCloud LTD.
##
### BEGIN INIT INFO
# Provides: opsagent
# Required-Start:
# Should-Start:
# Required-Stop:
# Should-Stop:
# Default-Start:  3 4 5
# Default-Stop:   0 6
# Short-Description: Opsagent Daemon
# Description: Runs opsagent
### END INIT INFO

OA_ROOT="/opsagent"

case "$1" in
  start)
    echo "Starting opsagent"
    ${OA_ROOT}/env/bin/opsagent -c /etc/opsagent.conf start
    ;;
  stop)
    echo "Stopping opsagent"
    ${OA_ROOT}/env/bin/opsagent stop
    ;;
  stop-wait)
    echo "Stopping opsagent"
    ${OA_ROOT}/env/bin/opsagent stop-wait
    ;;
  restart-wait)
    echo "Restarting opsagent"
    ${OA_ROOT}/env/bin/opsagent restart-wait
    ;;
  restart)
    echo "Restarting opsagent"
    ${OA_ROOT}/env/bin/opsagent /etc/opsagent.conf restart
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|stop-wait|restart-wait}"
    exit 1
    ;;
esac

exit 0
