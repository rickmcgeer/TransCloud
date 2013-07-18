
import sys
sys.path.insert(0, './mq/')
import taskmanager

grack06 = 'genericuser@grack06.uvic.trans-cloud.net'
# grack05 = 'genericuser@grack05.uvic.trans-cloud.net' # dead
grack04 = 'genericuser@grack04.uvic.trans-cloud.net'
grack03 = 'genericuser@grack03.uvic.trans-cloud.net'
grack02 = 'genericuser@grack02.uvic.trans-cloud.net'
grack01 = 'genericuser@grack01.uvic.trans-cloud.net'

uvic_cluster = [grack06,grack04,grack03,grack02,grack01]

all_clusters = [uvic_cluster]

# tmp dirs are different at different clusters. 
tmp_dirs = {"cs.UVic.CA":"/tmp/",
            "uvic.trans-cloud.net":"/tmp/",
            "undefined.location":'/tmp/'}

user_ids = {"cs.UVic.CA":"gis",
            "uvic.trans-cloud.net":"gis",
            "undefined.location":'gis'}

swift_proxies = {"cs.UVic.CA":"142.104.195.225",
                 "uvic.trans-cloud.net":"142.104.195.225",
                 "undefined.location":'142.104.195.225'}


class Cluster(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


    def validate(self):
        for prop in ['lat','lon', 'shortname', 'tmpdir', 'swiftproxys','fallbackswift' 'machines', 'baseip']:
            assert prop in self.__dict__, "Cluster is missing "+prop 


uvic_swift1 = '142.104.195.225'
uvic_swift2 = '142.104.195.226'

uvic = Cluster(   lat="48.4633",
                  lon="123.3118",
                  shortname="uvic",
                  tmpdir="/tmp/",
                  swiftproxys=[uvic_swift1, uvic_swift2],
                  fallbackswiftmachines=[uvic_swift1],
                  baseip="142.104")


def n_machines():
    """ How many machines are there? """
    n = 0
    for cluster in all_clusters:
        for machine in cluster:
            n += 1
    return n


def test_getclusters():
    assert n_machines() > 0, "Where are the machines?" 



def get_cluster_tmp_location():
    cluster_name = taskmanager.get_local_site_name()
    assert cluster_name in tmp_dirs, "%s not in tmp_dirs" % cluster_name
    return tmp_dirs[cluster_name]

    
def test_gettmp():
    assert get_cluster_tmp_location() in ['/mnt/','/tmp/']

def get_cluster_user_id():
    cluster_name = taskmanager.get_local_site_name()
    assert cluster_name in user_ids, "%s not in user_ids" % cluster_name
    return 'system:' + user_ids[cluster_name]

    
def test_getuserid():
    assert get_cluster_user_id() in ['system:gis']

def get_cluster_swift_proxy():
    cluster_name = taskmanager.get_local_site_name()
    assert cluster_name in swift_proxies, "%s not in swift_proxies" % cluster_name
    return  swift_proxies[cluster_name]

    
def test_swift_proxy():
    assert get_cluster_swift_proxy() in ['165.124.51.144']


def test_clusters():
    uvic.validate()
