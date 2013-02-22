import sys
import os
import greenspace
import json
import optparse
import settings
import tempfile
import clusters

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

NORTH_AMERICA=1
EUROPE=2


def populate_cities(ncities, testing_prefix="", testing=False):
     # get command line options
  
    print "Running with "+str(ncities)+" cities to process"
    here = os.path.dirname(os.path.realpath(__file__))+"/"
    cities = []
    

    greenspace.init()
    for cluster_nums in xrange(1,5): # these are the map clusters, not machine clusters 
         cities.append(greenspace.get_cities(cluster_nums, ncities))
    if testing:
         cities = []
         for i in xrange(0,ncities):
              cities.append([FAKE_CITY])

    print cities

    manager = taskmanager.TaskManager(prefix=testing_prefix)
    manager.reset()
    for i,city_batches in enumerate(cities):
         for city in city_batches:
              job = json.dumps(city ,separators=(',',':'))
              
              if testing:
                   manager.add_task({'task':'greencities','data':job})
              else:
                   manager.add_task({'task':'greencities','data':job}, decide_cluster(i))
              

    return manager.get_size()


def decide_cluster(map_cluster):
     """Given a map cluster, get a machine cluster number.  Basically schedule map clusters to machine clusters."""
     cluster_id = (map_cluster%len(clusters.all_clusters)) + 1
     return cluster_id

def test_decide_cluster():
     for i in xrange(1,6):
          assert 1 <= decide_cluster(i) <= len(clusters.all_clusters) 

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-c", "--num_cities", dest="num_cities", type="int", default=5, help="number of cities to run the calculation on")
    (options, args_not_used) = parser.parse_args()
    populate_cities(options.num_cities)
