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

class JSON_SQL_Query:
    def __init__(self, sqlQuery, resultsNameTuple, property_columns, formatTuple, geometry_column):
        self.sqlQuery = sqlQuery
        self.resultsNameTuple = resultsNameTuple
        self.property_columns = property_columns
        self.formatTuple = formatTuple
        self.geometry_column = geometry_column

json_sql_queries = {'allCities':JSON_SQL_Query("SELECT map.name, map.greenspace, ST_AsGeoJSON(map.the_geom) FROM map order by map.greenspace desc limit 10000", ("name", "greenspace", "geom"), [0, 1], ("%s", "%f", ""), 2),
                    'last10Cities':JSON_SQL_Query("SELECT map.name, map.greenspace, ST_AsGeoJSON(map.the_geom), processed.process_end_time FROM map INNER JOIN processed ON map.gid = processed.gid WHERE processed.file_path is not null order by processed.process_end_time desc limit 10;",  ("name", "greenspace", "geom", "time"), [0, 1], ("%s", "%f", "" ""), 2)
    }

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
    form = cgi.FieldStorage()
    query_name = form.getvalue("query")
    json_query = json_sql_queries[query_name]
    query = json_query.sqlQuery
    

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

    for resultTuple in results:
        response += '{"type": "Feature", "properties": {'
        entries = []
        for item_number in range(0, len(resultTuple)):
            if item_number not in json_query.property_columns: continue
            fmt_string = '"' + json_query.resultsNameTuple[item_number] + '" : "' + json_query.formatTuple[item_number] + '"'
            entries += [fmt_string % resultTuple[item_number]]
        properties = ', '.join(entries)
        response += properties + '},'
	response += '"crs" : {"type" : "OGC", "properties" : {"urn":"urn:ogc:def:crs:OGC:1.3:CRS84"}},'
        response += '"geometry" : %s},' % resultTuple[json_query.geometry_column]
        
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

    






