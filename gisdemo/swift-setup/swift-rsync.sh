#! /bin/bash


# create rsyncd config file
# the variables $fspath and $maxconn

cat >/tmp/rsyncd.conf <<EOF
uid = swift
gid = swift
log file = /var/log/rsyncd.log
pid file = /var/run/rsyncd.pid
address = 0.0.0.0

[account]
max connections = $maxconn
path = $fspath
read only = false
lock file = /var/lock/account.lock

[container]
max connections = $maxconn
path = $fspath
read only = false
lock file = /var/lock/container.lock

[object]
max connections = $maxconn
path = $fspath
read only = false
lock file = /var/lock/object.lock
EOF