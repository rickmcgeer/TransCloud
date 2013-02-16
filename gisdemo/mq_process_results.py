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


def process_results(prefix="", testing=False):
    submitted = []
    try:
        client = taskmanager.TaskClient(queue=prefix+taskmanager.RESULT_QUEUE_NAME)
	if not testing:
		greenspace.init()

        while(True):
            try:
                print "Getting new task:"
                new_job, jobid = client.get_task()
		if new_job == None:
			return submitted

                print new_job
                new_job = json.loads(new_job['result'])

		if not testing:
			submit_result(**new_job)
		submitted.append(new_job)

                client.report_done(jobid)
            except Exception as e:
                print str(e)
    finally:
        greenspace.close()

if __name__ == '__main__':
    
    process_results()
