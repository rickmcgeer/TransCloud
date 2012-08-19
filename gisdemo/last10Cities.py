import png
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
    connection = psycopg2.connect(database=GIS_DATABASE,
                                user=DB_USER,
                                password=DB_PASS)
    cursor = connection.cursor()

# table is processed(gid int, name varchar(256), file_path varchar(60),
#                    sever_name varchar(256), process_start_time timestamp,
#                    process_end_time timestamp)
    query = "select * FROM processed ORDER BY process_end_time DESC LIMIT 10"

    cursor.execute(query)
    results = cursor.fetchall()
    response = '['

    for (gid, cityName, cityFile, serverName, cityStartTime, cityEndTime) in results:
        response += '{"name": "%s", "processedTime": "%s", "imageURL": "http://%s/%s", "serverName":"%s%},' % (cityName, cityEndTime, cityURLPrefix, cityFile, serverName)
    response = response[:-1] # trim off the last ','
    response += ']'
    print "Content-type: text/html\n"
    print  response
except psycopg2.ProgrammingError as e:
    # dunno what to do here...

    






