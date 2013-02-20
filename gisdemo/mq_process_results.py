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

def submit_result(greenspace_val, id, name, stime, etime, imgname, servername, location):
        # append update statement to string
        update_stmnt = greenspace.pgConn.createUpdateStmnt(greenspace_val,
                                                id, name,
                                                stime, etime,
                                                imgname,
                                                servername, location)

        greenspace.pgConn.performUpdate(update_stmnt)
import traceback

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
                if 'result' in new_job and new_job['result'] != u'failure':
                        job = json.loads(new_job['result'])
                        print job['name'], "worked with", job['greenspace_val'], "greenspace in", job['imgname']
                        if not testing:
                                submit_result(**job)
                        submitted.append(job)
                else:
                        print new_job['result'], "on",new_job['name'],"with", new_job['message']
                        submitted.append(new_job)

                client.report_done(jobid)
            except ValueError as e:
                print traceback.format_exc()
                print type(e), str(e), "New Job:",type(new_job), new_job
            except Exception as e:
                print type(e), str(e)
                if testing:
                        raise e
    finally:
        greenspace.close()

if __name__ == '__main__':
    
    process_results()
