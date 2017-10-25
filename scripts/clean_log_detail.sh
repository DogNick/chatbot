#!/bin/bash
LATEST_N_DAY=168
LOG_DIR=/search/odin/chatbot/trunk/logs
cd $LOG_DIR
#ls bot-detail-log.2* | sort -t"-" -k3.5n -k4n -k5n |  awk -v n=$LATEST_N_DAY '{if(NR > n){print}}' | xargs rm -rf
#ls bot-detail-log.2* | sort -t"-" -k3.5n -k4n -k5.1,5.2n -k5.4,5.5n |  awk -v n=$LATEST_N_DAY '{if(NR > n){print}}'
ls bot-detail-log.2* | sort -t"-" -k4n -k5n | awk -v n=$LATEST_N_DAY '{if(NR > n){print}}' | xargs rm -rf
