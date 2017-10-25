#!/bin/bash

while read -u10 line 
do
    if [[ ${line:0:1} = "#" ]]
    then
        continue
    fi
    nohup ./chatbot_env_setup.expect ${line} &
    #./chatbot_env_setup.expect ${line}
done  10< nodes 
