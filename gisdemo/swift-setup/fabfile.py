from fabric.api import *
import sys
import socket



# TODO:
#  dont know how to set up with internal ip's right now
#  make ring distribution
#  back up swift.config and builders! (place into swift repo?)
#  chown device for storage nodes
#  fails for non bash shell
#  set up swift user as it didnt on northwestern for some reason


# nw2 = "stredger@alpha.hdoop.vikelab.emulab.net"
# nw3 = "stredger@beta-0.hdoop.vikelab.emulab.net"
# nw4 = "stredger@beta-1.hdoop.vikelab.emulab.net"


nw1 = "stredger@pc2.instageni.northwestern.edu"
nw2 = "stredger@pc3.instageni.northwestern.edu"
nw3 = "stredger@pc4.instageni.northwestern.edu"
nw4 = "stredger@pc5.instageni.northwestern.edu"


swift_workers = [nw1, nw2, nw3, nw4]
swift_proxies = [nw4]
localhost = ["localhost"]
swift_cluster = [nw1, nw2, nw3, nw4]

swift_worker_ips = ["165.124.51.141", "165.124.51.142", "165.124.51.143", "165.124.51.144"]



env.roledefs = {
    'swift-cluster':swift_cluster,
    'swift-workers':swift_workers,
    'swift-proxies':swift_proxies,
    'localhost':localhost
}

env.key_filename = "~/.ssh/st_rsa"



swift_script_dir = "./"




def cluster_rings():
    execute(create_rings)
    execute(distribute_rings)

# build these in /tmp somehow
@roles('localhost')
def create_rings(dev="swiftfs"):
 
    partpower = 18 # how large each partition is, 2^this_num
    repfactor = 3 # replication factor
    partmovetime = 1 # min hours between partition move
    weight = 100

    if len(swift_worker_ips) < repfactor:
        print "we are tring to have", repfactor, "replications on", len(swift_worker_ips), "swift workers!"
        sys.exit()

    local('swift-ring-builder account.builder create '+str(partpower)+' '+str(repfactor)+' '+str(partmovetime))
    local('swift-ring-builder container.builder create '+str(partpower)+' '+str(repfactor)+' '+str(partmovetime))
    local('swift-ring-builder object.builder create '+str(partpower)+' '+str(repfactor)+' '+str(partmovetime))

    zone = 0 # should be unique for each ip
    for ip in swift_worker_ips:
        local('swift-ring-builder account.builder add z'+str(zone)+'-'+ip+':6002/'+dev+' '+str(weight))
	local('swift-ring-builder container.builder add z'+str(zone)+'-'+ip+':6001/'+dev+' '+str(weight))
	local('swift-ring-builder object.builder add z'+str(zone)+'-'+ip+':6000/'+dev+' '+str(weight))
        zone += 1

    # verify the rings
    local('swift-ring-builder account.builder')
    local('swift-ring-builder container.builder')
    local('swift-ring-builder object.builder')

    # distribute the partitions evenly across the nodes
    local('swift-ring-builder account.builder rebalance')
    local('swift-ring-builder container.builder rebalance')
    local('swift-ring-builder object.builder rebalance')


@parallel
@roles('swift-cluster')
def distribute_rings():
    
    rings = ["account.ring.gz", "container.ring.gz", "object.ring.gz"]

    sudo('mkdir -p /etc/swift')
    sudo('chmod a+w /etc/swift')
    for ring in rings:
        put(ring, '/etc/swift/'+ring)
    sudo('chown -R swift:swift /etc/swift')


@parallel
@roles('swift-cluster')
def clean_rings():
   
    sudo('rm -f /etc/swift/*.ring.gz')
    




def proxy_config():
    execute(local_proxy)
    execute(cluster_proxy)


@roles('localhost')
def local_proxy(user="gis", passwd="uvicgis"):

    local('export user='+user+'; export passwd='+passwd+'; '+swift_script_dir+'/swift-pconfgen.sh')


@parallel
@roles('swift-proxies')
def cluster_proxy(host_addr="www.google.com"):

    sudo('mkdir -p /etc/swift')
    sudo('chmod a+w /etc/swift')
    put('/tmp/proxy-server.conf', '/etc/swift/proxy-server.conf')
   
    # get desired ip and put into config file 
    put(swift_script_dir+'getmyip.py', '/tmp/getmyip.py')
    sudo('perl -pi -e "s/0.0.0.0/`python /tmp/getmyip.py '+host_addr+'`/" /etc/swift/proxy-server.conf')
    sudo('perl -pi -e "s/-l 127.0.0.1/-l 0.0.0.0/" /etc/memcached.conf')
    sudo('service memcached restart')
    sudo('chown -R swift:swift /etc/swift')
    sudo('swift-init proxy start')



def storage_config():
    execute(storage_config_gen)
    execute(cluster_storage)


# we want this to be the complete path to the file system swift 
#  will use when we append, the 'dev' that is contained in the rings.
#  in the default case 'dev' holds swiftfs, and /srv/node/swiftfs is
#  the file system we use!
@roles('localhost')
def storage_config_gen(fs_path="/srv/node", max_conn=6):
  
    local('export fspath='+fs_path+'; export maxconn='+str(max_conn)+'; '+swift_script_dir+'swift-rsync.sh')
    local(swift_script_dir+'swift-ringconfig.sh')
    local(swift_script_dir+'swift-objexpconfig.sh')



@parallel
@roles('swift-workers')
def cluster_storage(host_addr="www.google.com", swiftfs_path="/srv/node/swiftfs"):

    sudo('rm -rf /etc/swift/account-server.conf /etc/swift/container-server.conf /etc/swift/object-server.conf')

    # set up ring config files
    sudo('mkdir -p /etc/swift')
    sudo('chmod a+w /etc/swift')
    put('/tmp/account-server.conf', '/etc/swift/')
    put('/tmp/container-server.conf', '/etc/swift/')
    put('/tmp/object-server.conf', '/etc/swift/')
    put(swift_script_dir+'getmyip.py', '/tmp/getmyip.py')
    sudo('perl -pi -e "s/0.0.0.0/`python /tmp/getmyip.py '+host_addr+'`/" /etc/swift/*-server.conf')

    # enable the rsync daemon
    put('/tmp/rsyncd.conf', '/etc/', use_sudo=True)
    sudo('perl -pi -e "s/RSYNC_ENABLE=false/RSYNC_ENABLE=true/" /etc/default/rsync')
    sudo('perl -pi -e "s/0.0.0.0/`python /tmp/getmyip.py '+host_addr+'`/" /etc/rsyncd.conf')
    sudo('service rsync start')

    # other config files
    put('/tmp/object-expirer.conf', '/etc/swift')

    sudo('chown swift:swift '+swiftfs_path)
    sudo('chown -R swift:swift /etc/swift')
    sudo('swift-init all start') # starts every swift process that has a config file




def cluster_keygen():

    execute(local_keygen)
    execute(distribute_key)



@roles('localhost')
def local_keygen():

    # we probably want to back up the file this generates somewhere!
    local(swift_script_dir+'swift-keygen.sh')


@parallel
@roles('swift-cluster')
def distribute_key():

    sudo('mkdir -p /etc/swift')
    sudo('chmod a+w /etc/swift')
    put('/tmp/swift.conf', '/etc/swift/swift.conf')
    sudo('chown -R swift:swift /etc/swift')
    



@parallel
@roles('swift-workers')
def setup_loop_device():

    dev = "swiftdisk"
    mntpt = "/srv/node/swiftfs"
    devpath = "/srv/"+dev
    disksize=1*1000000

    sudo('mkdir -p /srv')
    sudo('dd if=/dev/zero of='+devpath+' bs=1024 count=0 seek='+str(disksize))
    sudo('mkfs.xfs -i size=1024 '+devpath)
    sudo('echo "'+devpath+' '+mntpt+' xfs loop,noatime,nodiratime,nobarrier,logbufs=8 0 0" >> /etc/fstab')

    sudo('mkdir -p '+mntpt)
    sudo('mount '+mntpt)
    sudo('chown -R swift:swift '+mntpt)




@parallel
@roles('swift-cluster')
# we could separate into proxy and cluster
def install_swift_deps():

    with settings(warn_only=True):
        sudo('apt-get update')
    sudo('apt-get -y --force-yes install swift openssh-server swift-proxy memcached swift-account swift-container swift-object curl gcc git-core python-configobj python-coverage python-dev python-nose python-setuptools python-simplejson python-xattr sqlite3 xfsprogs python-webob python-eventlet python-greenlet python-pastedeploy python-netifaces')


@parallel
@roles('swift-cluster')
def swift_restart():
    sudo('swift-init all restart')



@parallel
@roles('swift-cluster')
def create_swift_user():
    sudo('useradd -r -s /bin/false swift')

@parallel
@roles('swift-cluster')
def create_memcached_user():
    sudo('useradd -r -s /bin/false memcache ')

def create_users():
    execute(create_swift_user)
    execute(create_memcached_user)


@parallel
@roles('swift-cluster')
def clean_files(files="proxy-server.conf"):
    sudo('rm -rf '+files)



@parallel
@roles('swift-cluster')
def test_ips():
    put(swift_script_dir+'getmyip.py', '/tmp/')
    run('python /tmp/getmyip.py')
    

@parallel
@roles('swift-proxies')
def test_memcached():
    put(swift_script_dir+'getmyip.py', '/tmp/')
    put(swift_script_dir+'memcachedtest.py', '/tmp/')
    run('python /tmp/memcachedtest.py')



def swift_install():
    execute(install_swift_deps)
    #execute(setup_loop_device)
    execute(cluster_keygen)
    execute(cluster_rings)
    execute(proxy_config)
    execute(storage_config)
