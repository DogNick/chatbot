pid=`ps -ef | grep server.py | grep -v grep| awk '{print $2}'`
echo "[pid="$pid"] killed"
kill -9 $pid
