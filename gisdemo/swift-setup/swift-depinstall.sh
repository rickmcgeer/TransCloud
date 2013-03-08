#! /bin/bash

# the wait commands dont really work... soooo we may have to run a few times

apt-get update
wait $!

# dependencies
apt-get -y install python-software-properties
wait $!

add-apt-repository ppa:swift-core/release 
wait $!

apt-get update
wait $!

# install swift core stuff
apt-get -y install swift openssh-server
wait $!

# proxy server stuff
apt-get -y install swift-proxy memcached
wait $!

# storage service stuff
apt-get -y install swift-account swift-container swift-object xfsprogs
wait $!

# other stuff
apt-get -y install curl gcc git-core python-configobj python-coverage python-dev python-nose python-setuptools python-simplejson python-xattr sqlite3 xfsprogs python-webob python-eventlet python-greenlet python-pastedeploy python-netifaces
wait $!