import sys
import os
import greencitieslog
import greenspace
import json
import optparse
import settings
import tempfile
import traceback
import mq_calc

sys.path.insert(0, './mq/')

import taskmanager

def process_cities(testing_prefix="", testing=False):
    client = taskmanager.TaskClient(prefix=testing_prefix)
    print "Processing:", client.queue, "queue."
    ndone = 0
    while(True):
            new_job, jobid = client.get_task()

            if new_job == None:
                return ndone

            os.chdir(settings.TEMP_FILE_DIR)
            greencitieslog.start()
            id, name, poly, bb1, bb2, bb3, bb4 = json.loads(new_job['data'])   
            if not testing:
                greenspace.init()
                green_results = greenspace.process_city(id,name,poly,(bb1,bb2,bb3,bb4),"all", testing=True)
            else:
                green_results = mq_calc.FAKE_RESULT

            client.report_done(jobid, {'task':'greencity', 'result':json.dumps(green_results)})
            ndone += 1
    greencitieslog.close()

if __name__ == '__main__':
    process_cities()
