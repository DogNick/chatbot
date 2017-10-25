#!/bin/bash
ulimit -n 10000
echo '128000' > /proc/sys/fs/file-max
sysctl -w net.core.somaxconn=65535
sysctl -w net.core.netdev_max_backlog=2500

mkdir -p ../logs
PORT=2048

lsof -i:$PORT | awk '{if(NR>1){print $2}}' | xargs -I {} kill -9 {}

rm ../logs/*.lock
cd ../bin/
nohup python -u server.py --log_verbose=1 --port=$PORT --env=online --service=weixin --mode=bj --procnum=16 --account=sogouwangzai 2>&1 | cronolog ../logs/wechat-log-%Y%m%d &
