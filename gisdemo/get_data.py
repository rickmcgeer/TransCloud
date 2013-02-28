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

sites =  {"cs.UVic.CA": {"cities": [4,8,10,11,16,23], "workers": [10,8,6,7,8,10], "nodes": [5,4,4,4,5,4]},
         "uvic.trans-cloud.net": {"cities": [4,8,10,11,16,23], "workers": [10,8,6,7,8,10], "nodes": [5,4,4,4,5,4]},
          "u-tokyo.ac.jp": {"cities": [6,7,8,9,10,12], "workers": [1,2,3,4,3,4], "nodes": [1,1,1,2,2,2]},
	  "informatik.tu-kaiserslautern.de": {"cities": [6,12,13,14,16,18], "workers": [12, 16, 18, 14, 16, 20], "nodes": [6, 8, 9, 7, 8, 10]},
	  ".ibbt.be": {"cities": [5,7,9,13, 17, 23], "workers": [2, 4, 8, 10, 8, 10], "nodes": [1, 2, 3, 5, 4, 5]},
	  "emulab.net": { "cities": [17, 23, 25, 31, 37, 46], "workers": [16, 16, 16, 14, 16, 16], "nodes": [6, 6, 4, 6, 6, 8]},
	  "northwestern.edu": { "cities": [153, 162, 168, 174, 180, 186], "workers": [16, 18, 20, 16, 18, 20], "nodes": [3, 4, 5, 3, 4, 5]}
	     }

# query: select count(*) from processed where cluster = cite (cities)
# select count(*_ from processed for total
# import clusters




## total = {}

## def sum_dict():
##     result = {}
##     for key in ["cities", "workers", "nodes"]:
##         this_total = sites["cs.UVic.CA"][key]
##         for site in sites:
##             if site == "cs.UVic.CA": continue
##             site_data = sites[site]
##             values = site_data[key]
##             for i in range(0, len(values)):
##                 this_total[i] += values[i]
##         total[key] = this_total

sys.stderr = sys.stdout


form = cgi.FieldStorage()
requested_site = form.getfirst("site", "total")


## if requested_site in sites:
##     return_data = sites[requested_site]
##     return_data['site_name'] = requested_site
## else:
##     sum_dict()
##     return_data = total
##     return_data['site_name'] = 'total'

db = dbObj.pgConnection()
return_data = db.getCGIValues(requested_site)

json_return = json.JSONEncoder().encode(return_data)
print "Content-Type: text/html"
print
print json_return
    
