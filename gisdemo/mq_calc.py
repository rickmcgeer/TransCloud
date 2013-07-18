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
    # we break the world into 4 'regions' so we select ncities from each region
    #for region_num in xrange(1,5):
    region_num = 1
    cities.extend(greenspace.get_cities(region_num, ncities))
    if testing:
         cities = []
         for i in xrange(0,ncities):
              cities.append([FAKE_CITY])

    print cities

    manager = taskmanager.TaskManager(prefix=testing_prefix)
    manager.reset()
    for i,city in enumerate(cities):
            job = json.dumps(city ,separators=(',',':'))
            if testing:
                manager.add_task({'task':'greencities','data':job})
            else:
                clust = decide_cluster(i, ncities)
                print ">> Enqueue", city[1], "on", taskmanager._sites[clust]
                manager.add_task({'task':'greencities','data':job}, clust )
              
    return manager.get_size()


def decide_cluster(city, ncities):
    """Given a map cluster, get a machine cluster number.  Basically schedule map clusters to machine clusters."""
    batch = city/4
    clus = batch % (len(taskmanager._sites) -1)
    
    return clus + 1

def test_decide_cluster():
    for i in xrange(0,32):
        print i,"-->",decide_cluster(i, 8)
        clus = decide_cluster(i, 5)
        assert 1 <= clus <= len(taskmanager._sites) 
        assert clus in taskmanager._sites, "Invalid site %d"%(clus)

    clusters = [0 for i in range(len(taskmanager._sites))]
    for i in xrange(0,100*4):
        clus = decide_cluster(i, 100)
        clusters[clus-1] += 1
    print str(clusters)
    assert 0 not in clusters, "Some cluster did not get jobs"+str(clusters)
        
if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-c", "--num_cities", dest="num_cities", type="int", default=5, help="number of cities to run the calculation on")
    (options, args_not_used) = parser.parse_args()
    populate_cities(options.num_cities)
