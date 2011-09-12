#!/bin/bash
identity="-i /home/cmatthew/.ssh/transcloud"
server=root@opencirrus-07510.hpl.hp.com

#hosts=""
hosts="opencirrus-07501.hpl.hp.com opencirrus-07502.hpl.hp.com opencirrus-07503.hpl.hp.com opencirrus-07504.hpl.hp.com opencirrus-07505.hpl.hp.com opencirrus-07506.hpl.hp.com opencirrus-07507.hpl.hp.com opencirrus-07508.hpl.hp.com opencirrus-07509.hpl.hp.com opencirrus-07510.hpl.hp.com opencirrus-07511.hpl.hp.com greenlight144.sysnet.ucsd.edu greenlight145.sysnet.ucsd.edu greenlight146.sysnet.ucsd.edu greenlight148.sysnet.ucsd.edu"
for target in $hosts
do
    tcssh="ssh $identity root@$target"
    echo "Installing packages on $target"
    $tcssh yum -y install ganglia-gmond
    $tcssh chkconfig gmond on
    $tcssh service gmond stop
    echo "Copying Template Config"
    cp -f ~/gmond.conf ~/gmond.tmp.conf
    echo $target
    target_ip=`dig $target +short`
    sed "s/xxx.xxx.xxx.xxx/$target_ip/" <gmond.tmp.conf >gmond.tmp2.conf
    scp $identity gmond.tmp2.conf root@$target:/etc/ganglia/
    $tcssh mv -f /etc/ganglia/gmond.tmp2.conf /etc/ganglia/gmond.conf
    $tcssh rm -rf /var/lib/ganglia/rrds/* 
    echo "Starting"
    $tcssh service gmond start
    echo "Done on $target" 
done

ssh $identity $server service gmond stop
ssh $identity $server  service gmetad stop

# ssh $identity root@opencirrus-07510.hpl.hp.com rm -rf /var/lib/ganglia/rrds/*

ssh $identity $server service gmetad start

ssh $identity $server service gmond start

ssh $identity $server service httpd restart

for target in $hosts
do
   tcssh="ssh $identity root@$target"
   $tcssh service gmond restart

done

for target in $hosts
do
   tcssh="ssh $identity root@$target"
   $tcssh service gmond status
   $tcssh df -h /
done
