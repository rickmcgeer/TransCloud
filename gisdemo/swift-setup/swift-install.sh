#! /bin/bash

# pretty much just following: 
# http://docs.openstack.org/developer/swift/howto_installmultinode.html

scriptdir=~/swift-setup

source ${scriptdir}/swift-envars.sh

# run this as root!!!
if [ "`whoami`" != "root" ]; then
    echo "Must run with root permissions!"
    exit
fi

if [ -z $STORAGE_LOCAL_NET_IP ]; then
    echo "please set STORAGE_LOCAL_NET_IP!"
    echo "see swift-envars.sh for details"
    exit
fi

if [ -z $PROXY_LOCAL_NET_IP ]; then
    echo "please set PROXY_LOCAL_NET_IP!"
    echo "see swift-envars.sh for details"
    exit
fi

if [ -z $DEVICE ]; then
    echo "please set DEVICE!"
    echo "see swift-envars.sh for details"
    exit
fi


swift-housekeep()
{
    echo "======================= Start Setup ========================="

    # config stuff
    mkdir -p /etc/swift
    chown -R swift:swift /etc/swift/

    # make unique string key, should be same for all nodes
    # generates /etc/swift/swift.conf
    source ${scriptdir}/swift-keygen.sh
    
    echo "======================= Done Setup ========================="
}


proxy-setup()
{
    echo "======================= Start Proxy ========================="

    if [ -z ${ISPROXY} ]; then
	echo "We are not a proxy node and therefore should not configure like one!"
	return
    fi

    partpower=${PARTPOWER} # 2^(the value) that the partition will be sized to.
    replfactor=${REPLICATION} # replication factor for objects
    partmovetime=${MINMOVETIME} # number of hours to restrict moving a partition more than once
    
    numzones=${ZONESPERNODE} # list of storage devs/node nums (should be 1 to n)

    cd /etc/swift

    #  use 0.0.0.0 to open to all connections
    perl -pi -e "s/-l 127.0.0.1/-l 0.0.0.0/" /etc/memcached.conf

    service memcached restart

    # Should generate /etc/swift/proxy-server.conf
    source ${scriptdir}/swift-pconfgen.sh

    cd /etc/swift
    swift-ring-builder account.builder create ${partpower} ${replfactor} ${partmovetime}
    swift-ring-builder container.builder create ${partpower} ${replfactor} ${partmovetime}
    swift-ring-builder object.builder create ${partpower} ${replfactor} ${partmovetime}

    dev=sdb1 # name of the fs we mounted
    weight=100
    zone=1

    # add self entries to the ring for each zone (storage dev)
    # for nzone in ${numzones}; do
    # 	swift-ring-builder account.builder add z${zone}-${STORAGE_LOCAL_NET_IP}:6002/${dev} ${weight}
    # 	swift-ring-builder container.builder add z${zone}-${STORAGE_LOCAL_NET_IP}:6001/${dev} ${weight}
    # 	swift-ring-builder object.builder add z${zone}-${STORAGE_LOCAL_NET_IP}:6000/${dev} ${weight}
    # 	let zone++
    # done

    #for each storage device in each storage node, add entries to the ring 
    for node in ${STORENODES}; do
	nip=$node
        #nip=`host ${node} | awk /[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ | cut -f4 -d \ `
	#if [ -z nip ]; then
	#    echo "Failed to add node ${node} to swift ring :("
	#    continue
	#fi
	for nzone in ${numzones}; do
	    swift-ring-builder account.builder add z${zone}-${nip}:6002/${dev} ${weight}
	    swift-ring-builder container.builder add z${zone}-${nip}:6001/${dev} ${weight}
	    swift-ring-builder object.builder add z${zone}-${nip}:6000/${dev} ${weight}
	    let zone++
	done
    done

    # verify the rings
    swift-ring-builder account.builder
    swift-ring-builder container.builder
    swift-ring-builder object.builder

    # rebalance rings
    swift-ring-builder account.builder rebalance
    swift-ring-builder container.builder rebalance
    swift-ring-builder object.builder rebalance
    wait $!

    # move to config (should be in for every node in cluster)
    mv *.builder /etc/swift
    mv *.ring.gz /etc/swift

    # figure out how to copy these better
    # for node in ${STORENODES}; do
    # 	scp /etc/swift/*.ring.gz ${scpuser}@${node}:~ 
    # done

    chown -R swift:swift /etc/swift

    # start proxy server
    swift-init proxy start

    # for emulab!!!
    # cp /etc/swift/swift.conf /users/${scpuser}/
    # cp /etc/swift/*ring.gz /users/${scpuser}/

    mkdir -p ~/cptostorage
    cp /etc/swift/swift.conf ~/cptostorage
    cp /etc/swift/*ring.gz ~/cptostorage


    echo "NOTE: Add more users in proxy-server.conf!"
    echo "Requests will only work for network interfaces that have associated users!"

    echo "======================= Done Proxy ========================="
}


swift-setup()
{
    echo "======================= Start Store ========================="

    cp ~/cptostorage/* /etc/swift # probs want to check if this fails!
    # but we may have the files there already... hmmm, warning then?

    # generate config file ans start rsync service
    source ${scriptdir}/swift-rsync.sh

    # generate config files for storage services
    source ${scriptdir}/swift-ringconfig.sh

    source ${scriptdir}/swift-objexpconfig.sh

    # one more time for good luck!
    chown -R swift:swift /etc/swift

    swift-init all start

    echo "======================= Done Store ========================="
}



device-setup()
{
    echo "======================= Start Dev ========================="

    dev=${DEVICE}
    mntpt=/srv/node/sdb1
    numzones=${NUMZONES}
    mkdir -p /srv

    if [ ${dev} == "sda4" ]; then

	devpath=/dev/${dev}
	fdisk /dev/sda<<EOF
t
4
83
w
EOF
	mkfs.xfs -i size=1024 ${devpath}
	echo "${devpath} $mntpt xfs noatime,nodiratime,nobarrier,logbufs=8 0 0" >> /etc/fstab

    elif [ ${dev} == "swift-disk" ]; then # loopback into file
	devpath=/srv/${dev}
	dd if=/dev/zero of=${devpath} bs=1024 count=0 seek=${SWIFTFSIZE}
   
	mkfs.xfs -i size=1024 ${devpath}
	echo "${devpath} $mntpt xfs loop,noatime,nodiratime,nobarrier,logbufs=8 0 0" >> /etc/fstab

    else # dont really know what to do!
	echo "-----------Unkown disk type!!----------------"
	echo "-----------Failed to mount disk!!----------------"
	return
    fi

    mkdir -p $mntpt
    mount $mntpt

    # for zone in ${numzones}; do
    # 	mkdir ${mntpt}/${zone}
    # done

    chown -R swift:swift $mntpt
    # mkdir /srv

    # for zone in ${numzones}; do
    # 	ln -s ${mntpt}/${zone} /srv/${zone}
    # 	mkdir -p /srv/${zone}/node/sdb${zone}
    # done    

    # mkdir -p /etc/swift/object-server /etc/swift/container-server /etc/swift/account-server  /var/run/swift

    #chown -R swift:swift /etc/swift /srv/[${zone}-${numzones}]/ /var/run/swift

    # rcfile="/etc/rc.local"
    # # may have to replace exit 0???
    # # perl -pi -e "s/exit 0//" $rcfile
    # echo "mkdir /var/cache/swift /var/cache/swift2 /var/cache/swift3 /var/cache/swift4" >> $rcfile
    # echo "chown swift:swift /var/cache/swift*" >> $rcfile
    # echo "mkdir /var/run/swift" >> $rcfile
    # echo "chown swift:swift /var/run/swift" >> $rcfile

    echo "======================= Done Dev ========================="
}


install-deps() {
    source ${scriptdir}/swift-depinstall.sh
}


# this has never worked....
swift-test() {

    cat > /etc/swift/dispersion.conf <<EOF
[dispersion]
auth_url = http://10.0.0.9:8080/auth/v1.0
auth_user = system:swift
auth_key = subterrania
EOF

    chown swift:swift /etc/swift/dispersion.conf 

    swift-dispersion-populate

    swift-dispersion-report

}



all()
{
    install-deps
    device-setup
    swift-housekeep
    proxy-setup
    swift-setup
}


if [ -z ${1} ]; then
    all
fi

while [ $1 ]; do
    case "${1}" in

	"all")
	    all
	    ;;

	"all-d")
	    device-setup
	    swift-housekeep
	    proxy-setup
	    swift-setup
	    ;;

	"all-dd")
	    swift-housekeep
	    proxy-setup
	    swift-setup
	    ;;

	"deps")
	    install-deps
	    ;;

	"dev")
	    device-setup
	    ;;

	"init")
	    swift-housekeep
	    ;;

	"proxy")
	    proxy-setup
	    ;;
	
	"store")
	    swift-setup
	    ;;

	"test")
	    #swift-test
	    echo "The dispersion test doesnt work!!"
	    ;;

	*)
	    echo "invalid option ${1}"
	    ;;
    esac
    shift
done

#
# http://docs.openstack.org/developer/swift/howto_installmultinode.html
#

# Get an X-Storage-Url and X-Auth-Token:
# curl -k -v -H 'X-Storage-User: system:root' -H 'X-Storage-Pass: testpass' https://$PROXY_LOCAL_NET_IP:8080/auth/v1.0
# curl -k -v -H 'X-Storage-User: system:gis' -H 'X-Storage-Pass: uvicgis' https://198.55.37.2:8080/auth/v1.0
# curl -k -v -H 'X-Storage-User: system:swift' -H 'X-Storage-Pass: subterrania' https://10.0.0.3:8080/auth/v1.0

# Check that you can HEAD the account:
# curl -k -v -H 'X-Auth-Token: <token-from-x-auth-token-above>' <url-from-x-storage-url-above>

# Check that swift works (at this point, expect zero containers, zero objects, and zero bytes):
# swift -A http://$PROXY_LOCAL_NET_IP:8080/auth/v1.0 -U system:root -K testpass stat
# swift -A https://10.0.0.3:8080/auth/v1.0 -U system:swift -K subterrania stat
# swift -A https://198.55.37.2:8080/auth/v1.0 -U system:gis -K uvicgis stat

# Use swift to upload a few files named ‘bigfile[1-2].tgz’ to a container named ‘myfiles’:
# swift -A https://$PROXY_LOCAL_NET_IP:8080/auth/v1.0 -U system:root -K testpass upload myfiles bigfile1.tgz
# swift -A https://$PROXY_LOCAL_NET_IP:8080/auth/v1.0 -U system:root -K testpass upload myfiles bigfile2.tgz

# Use swift to download all files from the ‘myfiles’ container:
# swift -A https://$PROXY_LOCAL_NET_IP:8080/auth/v1.0 -U system:root -K testpass download myfiles

# Use swift to save a backup of your builder files to a container named ‘builders’. Very important not to lose your builders!:
# swift -A https://$PROXY_LOCAL_NET_IP:8080/auth/v1.0 -U system:root -K testpass upload builders /etc/swift/*.builder

# Use swift to list your containers:
# swift -A https://$PROXY_LOCAL_NET_IP:8080/auth/v1.0 -U system:root -K testpass list

# Use swift to list the contents of your ‘builders’ container:
# swift -A https://$PROXY_LOCAL_NET_IP:8080/auth/v1.0 -U system:root -K testpass list builders

# Use swift to download all files from the ‘builders’ container:
# swift -A https://$PROXY_LOCAL_NET_IP:8080/auth/v1.0 -U system:root -K testpass download builders


# to benchmark
# swift-bench -A https://10.0.0.3:8080/auth/v1.0 -U system:swift -K subterrania -c 1 -s 10 -n 1 -g 1