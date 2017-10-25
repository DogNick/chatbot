#!/bin/bash

ulimit -n 10000
echo '128000' > /proc/sys/fs/file-max
sysctl -w net.core.somaxconn=65535
sysctl -w net.core.netdev_max_backlog=2500

cd `dirname $0`/../bin 
sh ../scripts/stop.sh
mkdir -p ../logs

rm ../logs/*.lock
#nohup python server.py --procnum=12 --log_verbose=0 --port=1024 --mode=gd --service=chaten --env=online 2>&1 | cronolog ../logs/qqgroup-log-%Y%m%d-%H & 
nohup python server.py --procnum=12 --log_verbose=0 --port=1024 --mode=dev --service=chaten --env=nick 2>&1 | cronolog ../logs/chaten-log-%Y%m%d-%H & 

#systemctl start crond
