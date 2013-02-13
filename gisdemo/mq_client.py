import sys
import os
import greencitieslog
import greenspace
import json
import optparse
import settings
import tempfile
import traceback

sys.path.insert(0, './mq/')

import taskmanager

def process_cities():

    client = taskmanager.TaskClient()
    print "Processing:", client.queue, "queue."
    while(True):
        try:
            new_job, jobid = client.get_task()
            os.chdir(settings.TEMP_FILE_DIR)
            greencitieslog.start()
            id, name, poly, bb1, bb2, bb3, bb4 = json.loads(new_job['data'])   
            greenspace.init()
            green_results = greenspace.process_city(id,name,poly,(bb1,bb2,bb3,bb4),"all", testing=True)
            client.report_done(jobid, {'task':'greencity', 'result':json.dumps(green_results)})
        except Exception as e:
            print str(e)
    greencitieslog.close()

if __name__ == '__main__':
    process_cities()


  
