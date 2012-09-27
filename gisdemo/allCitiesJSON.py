#!/usr/bin/python
import psycopg2
import math
import datetime
import sys
import os
import cgi
import cgitb
cgitb.enable()



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
#cityURLPrefix = "node1.gisdemo.vikelab.emulab.net/cityFiles"
cityURLPrefix = "gis.trans-cloud.net/cityFiles"

cityFilePrefix = "/var/www/cityFiles/"
blankFileName = "blank.jpg"

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
# table is map (gid int, name varchar(256), greenspace float, the_geom geometry)
#
    query = "SELECT map.name, map.greenspace, ST_AsGeoJSON(map.the_geom) FROM map order by map.greenspace desc limit 10000;"

    cursor.execute(query)
    results = cursor.fetchall()

    if not results:
         print "Content-type: text/html\n"
         response = '{"type": "FeatureCollection", "features" : ['
         for i in range(0, 10):
             response += '{"name":"", "greenspace":""},'
         response = response[:-1]
         response += ']}'
         print response
         exit(0)
    response = '{"type": "FeatureCollection", "features" : ['

    for (name, greenspace, geom) in results:
        response += '{"type": "Feature", "properties": { "name": "%s", "greenspace": "%f"},' % (name, greenspace)
	response += '"crs":{"type":"OGC", "properties":{"urn":"urn:ogc:def:crs:OGC:1.3:CRS84"}},'
        response += '"geometry": %s},' % geom   
    response = response[:-1] # trim off the last ','
    response += ']}'
    print "Content-type: text/html\n"
    print  response
except psycopg2.ProgrammingError as e:
    print "Content-type: text/html\n"
    response = "["
    for i in range(0, 10):
       response += '{"name":"", "greenspace":""},'
    response = response[:-1]
    response += ']'
    print response

    






