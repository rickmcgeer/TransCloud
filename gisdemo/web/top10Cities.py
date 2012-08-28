#!/usr/bin/python
import psycopg2
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

    query = "select name, greenspace from map where name is not null order by greenspace desc limit 10"

    cursor.execute(query)
    results = cursor.fetchall()

    if not results:
         print "Content-type: text/html\n"
         response = "["
         for i in range(0, 10):
             response += '{"name":"", "greenspace":""},'
         response = response[:-1]
         response += ']'
         print response
         exit(0)
    response = '['

    for (name, greenspace) in results:
        
        response += '{"name": "%s", "greenspace": "%f" },' % (name, greenspace)
    response = response[:-1] # trim off the last ','
    response += ']'
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

    






