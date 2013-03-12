#!/usr/bin/python
import psycopg2
import math
import datetime
import sys
import os
import cgi
import cgitb
import json
sys.path.append('/usr/local/src/greencities')
import dbObj
cgitb.enable()


sys.stderr = sys.stdout


form = cgi.FieldStorage()



db = dbObj.pgConnection()
return_data = db.getTop10Cities()

json_return = json.JSONEncoder().encode(return_data)
print "Content-Type: text/html"
print
print json_return
    
