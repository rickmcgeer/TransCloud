#!/bin/bash

# Install everything needed for greencities calculation

if [ "$(whoami)" != 'root' ]; then
        echo "You have no permission to run $0 as non-root user."
        exit 1;
fi

set -o errexit
apt-get -y --force-yes install python-pip python-dev
apt-get -y --force-yes install libpq-dev
pip install psycopg2
pip install pypng
pip install python-swiftclient
apt-get -y --force-yes install grass grass-dev gdal-bin



                                                                