CLUSTERS={'HP':'198.55.35.55', 'EMULAB':'155.98.38.233'}


SWIFT_PROXY1 = CLUSTERS['EMULAB']
SWIFT_PROXY2 = CLUSTERS['HP']
SWIFT_USER = "system:gis"
SWIFT_PWD = "uvicgis"
SWIFT_PNG_BUCKET = "completed"

# if the first proxy fails, fall back to this one
# currently set to HP
DEFAULT_SWIFT_HOST = "198.55.35.2"


IMG_LOC = "/tmp/"
IMG_EXT = ".png"

PRINT_DBG_STR = True # print to stdout

# The location of the logging file.
LOG_NAME = "green.log"

# database constants
DB_HOST = "green.cities.trans-cloud.net"
DB_USER = "root"
DB_PASS = ""
GIS_DATABASE = "world"

import os
import sys

# export GISDBASE=$HOME/grassdata
os.environ['GISDBASE'] = str(os.path.join(os.environ['HOME'], 'grassdata'))

# export GISBASE=/usr/lib/grass64
os.environ['GISBASE'] = "/usr/lib/grass64"

# export PYTHONPATH=$GISBASE/etc/python:$PYTHONPATH
pp = os.environ.get('PYTHONPATH', "")
os.environ['PYTHONPATH']  = os.path.join(os.environ['GISBASE'], 'etc/python')+":"+pp
sys.path.append(os.path.join(os.environ['GISBASE'], 'etc/python'))
# export PATH=$GISBASE/bin:$GISBASE/scripts:$PATH
os.environ['PATH'] = str(os.path.join(os.environ['GISBASE'], 'bin')) + ":" + os.environ['PATH']

# export LD_LIBRARY_PATH=$GISBASE/lib:$LD_LIBRARY_PATH
ld_path = os.environ.get('LD_LIBRARY_PATH', "")
os.environ['LD_LIBRARY_PATH'] = str(os.path.join(os.environ['GISBASE'], 'lib')) + ":" + ld_path

# export GIS_LOCK=$$
os.environ['GIS_LOCK'] = str(os.getpid())

# export GISRC=$HOME/.grassrc6
os.environ['GISRC'] = str(os.path.join(os.environ['HOME'], '.grassrc6'))

os.environ['LOCATION_NAME'] = "greenspace"

# Place for Temporary Files
MACHINE_TMP_DIR = '/mnt/disk1'

# This will be overwritten for this job in the entry point to the program -- set
# to a value here just to avoid dumb python errors
TEMP_FILE_DIR = '/mnt/disk1'


