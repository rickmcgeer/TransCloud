#!/usr/bin/python
import psycopg2
import sys
import os
import time
#import swiftclient.client

swiftURL = "http://swift.gcgis.trans-cloud.net:8080/auth/v1.0"
swiftUser = "system:gis"
swiftKey="uvicgis"

#swiftconnection = swiftclient.client.Connection(swiftURL, swiftUser, swiftKey)

swiftContainer = 'completed'
swiftExec = "/usr/local/bin/swift"
    
rootPath = '/var/www/cityFiles/'
# 
LOG_FILE = '/var/www/download.log'
logFile = open(LOG_FILE, 'a')

while True:
    try:
        connection = psycopg2.connect(database="world")
        cursor = connection.cursor()


        query = "select * FROM processed WHERE process_end_time IS NOT NULL and file_path IS NOT NULL ORDER BY process_end_time DESC;"

        cursor.execute(query)
        results = cursor.fetchall()


        for (gid, cityFileName, cityStartTime, cityEndTime, serverName) in results:
            cityCmdName = cityFileName.replace(" ", "\ ")
            cityFile = cityFileName.replace(" ", "_")
            path = rootPath + cityFile
            if os.path.exists(path): 
                continue
            try:
                # return_code = call([swiftExec, "-A " + swiftURL, "-U " + swiftUser, "-K " + swiftKey, "download %s %s" % (swiftContainer, cityFile), "-o " + path])
                cmdLine = "%s -A %s -U %s -K %s download %s %s -o %s" % (swiftExec, swiftURL, swiftUser, swiftKey, swiftContainer, cityCmdName, path)
                return_code = os.system(cmdLine)
                if return_code < 0:
                    print >>logFile, "Download %s was terminated by signal %d" % (cmdLine, -return_code)
                else:
                    print >> logFile, "Command %s executed succesfully" % cmdLine
            except OSError as e:
                print >> logfile, "Execution of download command %s failed: %s" % (cmdLine, e)
    except psycopg2.ProgrammingError as e:
	print >> logfile, "Postgres lookup failed:", e

    time.sleep(15)
print 'hello'
