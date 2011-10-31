#!/bin/bash
set -u 
set -e
set -x

                                                                   
                                             
# Create hadoop accounts
# Put install.tar.gz on all machines. 
# untar
# run "put all machines in known_hosts" script
# copy updated .bashrc
# unpack hadoop-0.20.2-chris.tar.bzip in home
# unpack pig in home
# ln -s /home/hadoop/jre1.6.0_24 /home/hadoop/java
# ln -s /home/hadoop/hadoop-0.20.2 /home/hadoop/hadoop
# ln -s /home/hadoop/pig-0.8.0 /home/hadoop/pig
# Put hosts file in place:
# 	mv hosts hosts.newbak
# 	cp /home/hadoop/install/hosts.txt hosts
# Make hadoop temp dir
# 	mkdir /home/hadoop/hadoop-datastore

# Prep Hadoop
# 	hadoop-env.sh:
# 		JAVA_HOME
# 	core-site.xml
# 		tmp.dir
# 		fs.default.name
# 	masters
# 	slaves
	
# *** format the HDFS on all nodes
# hadoop namenode -format




#identity="-i /home/cmatthew/.ssh/transcloud"
identity=""

skip_check="-o StrictHostKeyChecking=no"




ssh root@ns.trans-cloud.net TransCloud/dns/bind9.py



hd_master="198.55.37.134"

hosts="198.55.37.134 198.55.37.133 198.55.37.138"

for target in $hosts
do
    tcssh="ssh $skip_check $identity root@$target"
    echo "Setting up user account"
    set +e
    $tcssh useradd -d /home/hadoop -m hadoop
    set -e
    jre_file="jre1.6.0_24.tar.gz"
    install_file="install.tar.gz"
    echo "Cleanup"
    $tcssh "rm -rf /home/hadoop/jre*"
    $tcssh "rm -rf /home/hadoop/install"
    $tcssh "rm -rf /home/hadoop/pig-0.8.0"
    $tcssh "rm -rf /home/hadoop/hadoop-0.20.2"
    echo "Copy Files"
    scp $identity $skip_check $install_file root@$target:/home/hadoop/ 
    scp $identity $skip_check $jre_file root@$target:/home/hadoop/ 
    scp $identity $skip_check .bashrc root@$target:/home/hadoop/ 


    echo "Unzip Files"
    $tcssh "cd /home/hadoop; tar xzf $install_file"
    $tcssh "cd /home/hadoop; tar xjf install/hadoop-0.20.2-chris.tar.bzip"
    $tcssh "cd /home/hadoop; tar xzf install/pig-0.8.0.tar.gz"
    $tcssh "cd /home/hadoop; tar xkf $jre_file"

    $tcssh "rm -rf /home/hadoop/$jre_file"
    $tcssh "rm -rf /home/hadoop/$install_file"

    echo "Linking"
    $tcssh ln -s /home/hadoop/hadoop-0.20.2 /home/hadoop/hadoop
    $tcssh ln -s /home/hadoop/jre1.6.0_24 /home/hadoop/java
    $tcssh ln -s /home/hadoop/pig-0.8.0/ /home/hadoop/pig

    echo "Setup empty datastore"
    ds="/home/hadoop/hadoop-datastore"
    $tcssh mkdir -p $ds
    $tcssh chmod 777 $ds

    $tcssh chown -R hadoop:hadoop /home/hadoop
    echo "Done on $target" 
done



echo "Finished preping $hosts"


