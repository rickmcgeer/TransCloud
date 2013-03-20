#!/usr/bin/python

import sys
import os
import cgi
import cgitb
import json
sys.path.append('/usr/local/src/greencities')
sys.path.append('/usr/local/src/greencities/mq')
#sys.path.insert(0, './mq')
import mq

cgitb.enable()
sys.stderr = sys.stdout

all_queues = mq.all_queues()
#result = {'queues':[]}
result = {}
for queue in all_queues:
    result[queue] = mq.sizeof(queue)
#    result['queues'].append(queue)

json_return = json.JSONEncoder().encode(result)
print "Content-Type: text/html"
print
print json_return

