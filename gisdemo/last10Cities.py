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
#cityURLPrefix = "green.cities.trans-cloud.net/cityFiles"
cityURLPrefix = "198.55.35.2:8080/v1/AUTH_system/completed"

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
    #ca_query = "select processed.gid,  processed.file_path, processed.process_end_time, ca_cities.name, processed.server_name from processed inner join ca_cities on ca_cities.gid = processed.gid where process_end_time is not null order by process_end_time desc limit 10"
    #us_query = "select processed.gid,  processed.file_path, processed.process_end_time, us_cities.name, processed.server_name from processed inner join us_cities on us_cities.gid = processed.gid where process_end_time is not null order by process_end_time desc limit 10"

    all_query = "select processed.gid,  processed.file_path, processed.process_end_time, map.name, processed.server_name, map.greenspace from processed inner join map on map.gid = processed.gid where process_end_time is not null order by process_end_time desc limit 10"

    all_query = """
    select processed.gid,
       processed.file_path,
       processed.process_end_time,
       map.name,
       processed.server_name,
       map.greenspace,
       ST_AsText(ST_Transform(ST_Centroid(map.the_geom), 4326)),
       ST_AsText(ST_Transform(map.the_geom, 4326)),
       ST_Area(map.the_geom)
    from
      processed inner join map on map.gid = processed.gid
    where
      process_end_time is not null
      order by process_end_time desc;"""

    cursor.execute(all_query)
    results = cursor.fetchall()

    assert results, "Database Query Failed"
        
    response = '['

    new = []
    print "Content-type: text/html\n"    
    for tup in results:
        new.append(tup)

    for (gid, fileName, cityEndTime, cityName, serverName, greenspace, point, poly, area) in new:
        try:
            assert gid > 0, "Invalid GID"
            cityEndTimeStr = cityEndTime.strftime("%Y-%m-%d %H:%M")
            assert len(str(cityEndTime)) > 1, "No City End time"
            ## if not fileName: 
            ##     passedFileName = blankFileName
            ## elif os.path.exists(cityFilePrefix+fileName): 
            ##     passedFileName = fileName
            ## else: 
            ##     passedFileName = blankFileName
        #serverName = serverName[serverName.rindex("/")+1:]
        
            response += '{"name": "%s", "processedTime": "%s", "imageURL": "http://%s/%s", "serverName":"%s", "greenspace":"%s","point":"%s", "poly":"%s"},' % (cityName, cityEndTimeStr, cityURLPrefix, fileName, serverName, greenspace, point, poly)
        except Exception,  e:
            print str(e)
    response = response[:-1] # trim off the last ','
    response += ']'
    print  response

except psycopg2.ProgrammingError as e:
    assert False, str(e)

    






