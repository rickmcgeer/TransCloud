#!/bin/bash

# Install everything needed for greencities calculation

if [ "$(whoami)" != 'root' ]; then
        echo "You have no permission to run $0 as non-root user."
        exit 1;
fi

apt-get -y --force-yes install python-pip python-dev build-essential python-numpy python-numpy-dev python-scipy proj
apt-get -y --force-yes install libpq-dev
pip install psycopg2
pip install pypng
pip install python-swiftclient

wget http://download.osgeo.org/gdal/gdal-1.9.1.tar.gz
tar zxf gdal-1.9.1.tar.gz
cd gdal-1.9.1
./configure --with-python --prefix=/usr/local
make -j8 all
make install
ldconfig


#apt-get -y --force-yes install 



                                                                