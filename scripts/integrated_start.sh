#!/bin/bash
ulimit -n 10000
echo '128000' > /proc/sys/fs/file-max
sysctl -w net.core.somaxconn=65535
sysctl -w net.core.netdev_max_backlog=2500

sh stop.sh

mkdir -p ../logs
cd ../bin/
nohup python server.py --log_verbose=1 --procnum=12 --port=1024 --mode=bj --service=chatbot --source=dummy --loglevel=info 2>&1 | cronolog ../logs/integrated-log-%Y%m%d &
#nohup python server.py --log_verbose=1 --env=cyy --procnum=12 --port=1024 --mode=bj --service=chatbot --source=dummy 2>&1 | cronolog ../logs/integrated-log-%Y%m%d &
