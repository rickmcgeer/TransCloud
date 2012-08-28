#! /bin/bash


export GISDBASE=$HOME/grassdata
export GISBASE=/usr/lib/grass64
export PYTHONPATH=$GISBASE/etc/python:$PYTHONPATH
export PATH=$GISBASE/bin:$GISBASE/scripts:$PATH
export LD_LIBRARY_PATH=$GISBASE/lib:$LD_LIBRARY_PATH
export GIS_LOCK=$$
export GISRC=$HOME/.grassrc6


# http://grass.fbk.eu/grass62/manuals/html62_user/grass6.html
