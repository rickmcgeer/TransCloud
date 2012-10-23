#!/usr/bin/python
import psycopg2
import math
import datetime
import sys
import cgi
import cgitb
cgitb.enable()

# these correspond to the selected column num in the SQL statement
GID = 0
CITY_NAME = 1
CV_HULL = 2
XMIN = 3
YMIN = 4
XMAX = 5
YMAX = 6


# val of all pixels we want the space around the polygon to be
MASK_COLOUR = 0


# database constants
DB_USER = "postgres"
DB_PASS = ""
GIS_DATABASE = "gisdemo"
PY2PG_TIMESTAMP_FORMAT = "YYYY-MM-DD HH24:MI:SS:MS"

CITY_TABLE = "cities"#"map"#"cities"
ID_COL = "gid"
NAME_COL = "name"
GEOM_COL = "the_geom"
GREEN_COL = "greenspace"

IMG_TABLE = "times"
IMG_NAME_COL = "file_path"
START_T_COL = "process_start_time"
END_T_COL = "process_end_time"
SERV_NAME_COL = "server_name"
cityURLPrefix = "node1.gisdemo.vikelab.emulab.net/cityFiles"


# dict for worldwide wms servers
WMS_SERVER = {'canada':"http://ows.geobase.ca/wms/geobase_en", 'us':None}

# 
LOG_FILE = None
LOG_NAME = "getmap.log"

try:
    ## connection = psycopg2.connect(database=GIS_DATABASE,
    ##                             user=DB_USER,
    ##                             password=DB_PASS)
    connection = psycopg2.connect(database="world")
    cursor = connection.cursor()

# table is processed(gid int, name varchar(256), file_path varchar(60),
#                    sever_name varchar(256), process_start_time timestamp,
#                    process_end_time timestamp)
    cursor.execute('select COUNT(*) from processed where process_end_time IS NOT NULL')
    result = cursor.fetchone()
    response = '{"total":%d}' % result

    print "Content-type: text/html\n"
    print  response
except psycopg2.ProgrammingError as e:
    # dunno what to do here..
    print "Content-type: text/html\n"
    print '{"total":0}'

    






