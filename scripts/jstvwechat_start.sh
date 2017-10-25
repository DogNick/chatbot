#!/bin/bash
ulimit -n 10000
echo '128000' > /proc/sys/fs/file-max
sysctl -w net.core.somaxconn=65535
sysctl -w net.core.netdev_max_backlog=2500

mkdir -p logs

PORT=2048

lsof -i:$PORT | awk '{if(NR>1){print $2}}' | xargs -I {} kill -9 {}

cd ../bin/
nohup python -u server.py --log_verbose=0 --port=$PORT --service=weixin --mode=bj --procnum=16 --account="jstvyzdd" 2>&1 | cronolog ../logs/jstvwechat-log-%Y%m%d &
