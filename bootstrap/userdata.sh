#!/bin/bash
#app_id=@{app_id}
OA_USER="root"
OA_DIR="/etc/opsagent.d"
OA_LOG="/var/log/opsagent"
mkdir -p $OA_DIR
mkdir -p $OA_LOG
if [ ! -f $OA_DIR/token ]; then
    ssh-keygen -b 2048 -q -P '' -f $OA_DIR/token
    rm -f $OA_DIR/token.pub
fi
chown $OA_USER:root $OA_DIR/token
chmod 400 $OA_DIR/token
if [ ! -f ${OA_LOG}/bootstrap.log ]; then
    touch ${OA_LOG}/bootstrap.log
fi
chown root:root ${OA_LOG}/bootstrap.log
chmod 640 ${OA_LOG}/bootstrap.log
if [ ! -f ${OA_LOG}/agent.log ]; then
    touch ${OA_LOG}/agent.log
fi
chown ${OA_USER}:root ${OA_LOG}/agent.log
chmod 640 ${OA_LOG}/agent.log
cat <<EOF > $OA_DIR/bootstrap.sh
#!/bin/bash
# if exists
if [ -d "$OA_ROOT" ]; then
    # TODO remove
    echo "$OA_ROOT exists"
else
    curl -sSL https://s3.amazonaws.com/visualops/bootstrap.sh | bash
    echo "opsagent installed"
    sleep 1
    service opsagentd start
fi
exit 0
EOF
chown root:root $OA_DIR/bootstrap.sh
chmod 500 $OA_DIR/bootstrap.sh
CRON=$(crontab -l | grep bootstrap.sh | wc -l)
if [ $CRON -eq 0 ]; then
    echo "*/5 * * * * ${OA_DIR}/bootstrap.sh >> ${OA_LOG}/bootstrap.log 2>&1" | crontab
fi
exit 0
# EOF
