Example crontab:

0 0 * * * touch /myth/video/vidcast/subscriptions /myth/video/vidcast/pip.log ; find /myth/video/vidcast/ -mtime +14 -type f -exec rm -f {} \;
0 5,11,15,20 * * * pa.py -d /myth/video/vidcast/ -m video ; mythutil --scanvideos 2>&1 > /dev/null
