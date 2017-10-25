#!/bin/bash

ulimit -n 10000
echo '128000' > /proc/sys/fs/file-max
sysctl -w net.core.somaxconn=65535
sysctl -w net.core.netdev_max_backlog=2500

cd `dirname $0`/../bin
sh ../scripts/stop.sh
mkdir -p ../logs

rm ../logs/*.lock
nohup python server.py --procnum=12 --log_verbose=1 --port=1024 --mode=bj --service=samsung --env=online 2>&1 | cronolog ../logs/samsung-log-%Y%m%d-%H &

#systemctl start crond
