#! /bin/bash

# this must be sourced as we need these vars in our current shell!!


export PROXYNODE="10.0.0.9"

#"alpha.multiswift.vikelab.emulab.net"

export STORENODES="10.0.0.9 10.0.0.8 10.0.0.7 10.0.0.6 10.0.0.5 10.0.0.3"

#"beta-0.multiswift.vikelab.emulab.net beta-1.multiswift.vikelab.emulab.net beta-2.multiswift.vikelab.emulab.net beta-3.multiswift.vikelab.emulab.net beta-4.multiswift.vikelab.emulab.net beta-5.multiswift.vikelab.emulab.net beta-6.multiswift.vikelab.emulab.net beta-7.multiswift.vikelab.emulab.net"


# should be nodes ip addr?? Dont know how to uniquely id that...
#sip=`ifconfig | grep -e "inet addr:[0-9]\{3\}.*Bcast" | cut -f2 -d \: | cut -f1 -d \  | tr -d ' '`
sip=`ifconfig | grep -e "inet addr:10.*Bcast" | cut -f2 -d \: | cut -f1 -d \  | tr -d ' '`
export STORAGE_LOCAL_NET_IP=$sip
echo "Local ip addr = $sip"

# this should be the ip of the proxy node
#pip=`host ${PROXYNODE} | awk /[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ | cut -f4 -d \  | tr -d ' '`
pip=$PROXYNODE
export PROXY_LOCAL_NET_IP=$pip
echo "Proxy ip addr = $pip"

if [ $sip == $pip ]; then
#if [ $sip == "10.0.0.9" ]; then
    export ISPROXY=1
    echo "We are a proxy node!"
fi

# for actual external device
#export DEVICE=sda4

# for local loopback
export DEVICE=swift-disk
# 490 gigs!
export SWIFTFSIZE=$((490*1000000))


export PARTPOWER=18 # how big each partition is as 2^(this num) 
export REPLICATION=3 # num times things are replicated
export MINMOVETIME=1 # move time in hours

numnodes=0
for node in $STORENODES; do
    numnodes=$(($numnodes+1))
done

if [[ ${REPLICATION} -gt ${numnodes} ]]; then
    echo "Replication factor greater than total num of storage nodes!! Fix this in swift-envars.sh!!"
    exit
fi


# should be 1 for multinode setup, but must be a list
export ZONESPERNODE="1"




export scpuser=root