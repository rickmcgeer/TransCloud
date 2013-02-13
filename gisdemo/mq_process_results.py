import sys
import os
import greencitieslog
import greenspace
import json
import optparse
import settings
import tempfile
import traceback
import time
sys.path.insert(0, './mq/')

import taskmanager

def submit_result(greenspace_val, gid, cityname, stime, etime, imgname, servername, location):
        # append update statement to string
        update_stmnt = greenspace.pgConn.createUpdateStmnt(greenspace_val,
                                                gid, cityname,
                                                stime, etime,
                                                imgname,
                                                servername, location)

        greenspace.pgConn.performUpdate(update_stmnt)

def process_results():
    try:
        client = taskmanager.TaskClient(queue=taskmanager.RESULT_QUEUE_NAME)
        greenspace.init()
        while(True):
            try:
                print "Getting new task:"
                new_job, jobid = client.blocking_get_task()

                print new_job
                new_job = json.loads(new_job['result'])
    
                submit_result(**new_job)
                print "Submitted:", new_job
                client.report_done(jobid)
            except Exception as e:
                print str(e)
    finally:
        greenspace.close()

if __name__ == '__main__':
    
    process_results()
