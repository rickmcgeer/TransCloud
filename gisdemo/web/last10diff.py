#!/usr/bin/python
import psycopg2
import math
import datetime
import sys
import os
import cgi
import cgitb
cgitb.enable()

form = cgi.FieldStorage()

assert 'gid' in form.keys(), "Gid not passed as a parameter"

gid = form['gid'].value
#gid = "7823"

#cityURLPrefix = "node1.gisdemo.vikelab.emulab.net/cityFiles"
cityURLPrefix = "green.cities.trans-cloud.net/cityFiles"

cityFilePrefix = "/var/www/cityFiles/"
blankFileName = "blank.jpg"

try:

    connection = psycopg2.connect(database="world")
    cursor = connection.cursor()

# table is processed(gid int, name varchar(256), file_path varchar(60),
#                    sever_name varchar(256), process_start_time timestamp,
#                    process_end_time timestamp)
    #ca_query = "select processed.gid,  processed.file_path, processed.process_end_time, ca_cities.name, processed.server_name from processed inner join ca_cities on ca_cities.gid = processed.gid where process_end_time is not null order by process_end_time desc limit 10"
    #us_query = "select processed.gid,  processed.file_path, processed.process_end_time, us_cities.name, processed.server_name from processed inner join us_cities on us_cities.gid = processed.gid where process_end_time is not null order by process_end_time desc limit 10"
    assert len(gid) > 1, "No gid supplied!"

    #time_query = "select file_path from (select process_end_time from processed where gid = "+gid+") as S, processed as P where P.process_end_time > S.process_end_time;"

    #all_query = "select processed.gid,  processed.file_path, processed.process_end_time, map.name, processed.server_name, map.greenspace from processed inner join map on map.gid = processed.gid where process_end_time is not null order by process_end_time desc limit 10"

    all_query = "select R.gid, R.file_path, R.process_end_time, map.name, R.server_name, map.greenspace, ST_AsText(ST_Transform(ST_Centroid(map.the_geom), 4326)), ST_AsText(ST_Transform(map.the_geom, 4326)), ST_Area(map.the_geom) from (select * from  processed where process_end_time > (select process_end_time from processed where gid = "+gid+")) as R inner join map on map.gid = R.gid order by R.process_end_time desc limit 10;"

    cursor.execute(all_query)
    results = cursor.fetchall()

    assert results, "Database Query Failed"
        
    response = '['

    new = []
    for tup in results:
        new.append(tup)
        
    for (gid, fileName, cityEndTime, cityName, serverName, greenspace, point, poly, area) in sorted( new, key=lambda tup: tup[8]):
        assert gid > 0, "Invalid GID"
        cityEndTimeStr = str(cityEndTime)
        assert len(str(cityEndTime)) > 1, "No City End time"
        cityEndTimeStr = cityEndTimeStr[:cityEndTimeStr.index(".")]
        if not fileName: 
            passedFileName = blankFileName
	elif os.path.exists(cityFilePrefix+fileName): 
            passedFileName = fileName
        else: 
            passedFileName = blankFileName
        #serverName = serverName[serverName.rindex("/")+1:]
        
        response += '{"name": "%s", "processedTime": "%s", "imageURL": "http://%s/%s", "serverName":"%s", "greenspace":"%s","point":"%s", "poly":"%s"},' % (cityName, cityEndTimeStr, cityURLPrefix, passedFileName, serverName, greenspace, point, poly)
    response = response[:-1] # trim off the last ','
    response += ']'
    print "Content-type: text/html\n"
    print  response

except psycopg2.ProgrammingError as e:
    assert False, str(e)
