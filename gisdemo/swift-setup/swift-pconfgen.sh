#! /bin/bash

# generates a proxy server config file
#  expects $user and $passwd to be defined
#  and writes 0.0.0.0 where the proxies ip address 
#  should go

cat >/tmp/proxy-server.conf <<EOF
[DEFAULT]
#cert_file = /etc/swift/cert.crt
#key_file = /etc/swift/cert.key
bind_port = 8080
workers = 8
user = swift

[pipeline:main]
pipeline = healthcheck cache tempauth proxy-server

[app:proxy-server]
use = egg:swift#proxy
allow_account_management = true
account_autocreate = true

[filter:tempauth]
use = egg:swift#tempauth
user_system_${user} = ${passwd} .admin http://0.0.0.0:8080/v1/AUTH_system

[filter:healthcheck]
use = egg:swift#healthcheck

[filter:cache]
use = egg:swift#memcache
memcache_servers = 0.0.0.0:11211
EOF
