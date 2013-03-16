import sys
import os
import greencitieslog
import greenspace
import landsatImg
import json
import optparse
import settings
import tempfile
import traceback
import mq_calc
import gcswift

sys.path.insert(0, './mq/')

import taskmanager

def process_cities(testing_prefix="", testing=False):
    client = taskmanager.TaskClient(prefix=testing_prefix)
    print "Processing:", client.queue, "queue."
    ndone = 0
    while(True):
        results = client.get_task()

        if results == None or results == (None,None):
            return ndone

        new_job, jobid = results
        os.chdir(settings.TEMP_FILE_DIR)
        greencitieslog.start()
        print new_job, jobid
        try:
            if not testing:
                greenspace.init()
            
                green_results = greenspace.process_city_from_json(new_job['data'], testing=testing)
            else:
                green_results = mq_calc.FAKE_RESULT
        except IOError as e:
            # no matter what, on ioerror die, we are probably out of space.
            print str(e)
            sys.exit(1)
            raise e
        except gcswift.MissingSwiftFile as e:
            client.report_done(jobid, {'task':'greencity', 'name':"fixme", 'result':'failure','message':e.message.translate(None,"\n\\/'")})
        except landsatImg.MissingCoverage as e:
            client.report_done(jobid, {'task':'greencity', 'name':"fixme", 'result':'failure','message':e.message.translate(None,"\n\\/'")})

        except Exception as e:
            if settings.PRODUCTION_MODE:
                client.report_done(jobid, {'task':'greencity', 'name':"fixme", 'result':'failure','message':str(e).translate(None,"\n\\/'")})
            else:
                raise e
        else:
            client.report_done(jobid, {'task':'greencity', 'result':json.dumps(green_results)})
        ndone += 1
    greencitieslog.close()

if __name__ == '__main__':
    process_cities()
