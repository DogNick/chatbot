#!/bin/bash

#NGINX_SERVER="root@10.153.58.67 chatbot@2017online"
DEST_DIR=/search/odin/chatbot/trunk
while read -u10 line 
do
    if [[ ${line:0:1} = "#" ]]
    then
        continue
    fi
    DEST=${line%% *} 
    echo " ===========================  Sync and restart "$DEST" ==================================="
    #ssh $DEST "cd $DEST_DIR;git reset;git checkout .;git pull" 
    ssh $DEST "cd $DEST_DIR;svn up;" 
    ssh -n -f $DEST "cd $DEST_DIR;sh stop.sh;sh start.sh > /dev/null 2>&1 &"
    #ssh -n -f $DEST "cd $DEST_DIR;git checkout -- .; git pull;sh stop.sh;"
done 10< nodes 

#DEST=${NGINX_SERVER%% *} 
#scp nginx.conf $DEST:/etc/nginx/
#ssh $DEST "cd $DEST_DIR; sh env/start_nginx.sh"
