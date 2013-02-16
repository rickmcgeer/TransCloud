import sys
import os
import greenspace
import json
import optparse
import settings
import tempfile

sys.path.insert(0, './mq/')

import taskmanager

FAKE_RESULT = {'id':100,
                   'name':'foobar',
                   'greenspace_val':0.5,
                   'stime':"1994-11-05T13:15:30Z",
                   'etime':"1994-11-05T13:17:30Z",
                   'imgname':'foobar.png',
                   'servername':'testserver',
                   'location':'fake location'
                   }

FAKE_CITY = {'id':100,
                   'name':'foobar',
                   'poly':'POLY(1,2,3,4)',
                   'bb1':100,
                   'bb2':200,
                   'bb3':300,
                   'bb4':100
                   }

def populate_cities(ncities, testing_prefix="", testing=False):
     # get command line options
  
    print "Running with "+str(ncities)+" cities to process"
    here = os.path.dirname(os.path.realpath(__file__))+"/"
    cities = []
    
    if not testing:
         greenspace.init()
         cities = greenspace.get_cities(1, ncities)
    else:
         for i in xrange(0,ncities):
              cities.append(FAKE_CITY)

    manager = taskmanager.TaskManager(prefix=testing_prefix)
    manager.reset()
    for i,c in enumerate(cities):
         job = json.dumps(c ,separators=(',',':'))
         manager.add_task({'task':'greencities','data':job},1)

    return manager.get_size(1)

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-c", "--num_cities", dest="num_cities", type="int", default=5, help="number of cities to run the calculation on")
    (options, args_not_used) = parser.parse_args()
    populate_cities(options.num_cities)
