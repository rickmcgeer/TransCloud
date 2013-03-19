
br01='cmatthew@' 'PC.transgeo.pgeni-gpolab-bbn-com.wall3.test.ibbt.be'
br02='cmatthew@' 'PC-0.transgeo.pgeni-gpolab-bbn-com.wall3.test.ibbt.be'
br03='cmatthew@' 'PC-1.transgeo.pgeni-gpolab-bbn-com.wall3.test.ibbt.be'
br04='cmatthew@' 'PC-2.transgeo.pgeni-gpolab-bbn-com.wall3.test.ibbt.be'

brussels_cluster = [br01,br02,br03,br04]

grack06 = 'genericuser@grack06.uvic.trans-cloud.net'
grack05 = 'genericuser@grack05.uvic.trans-cloud.net'
grack04 = 'genericuser@grack04.uvic.trans-cloud.net'
grack03 = 'genericuser@grack03.uvic.trans-cloud.net'
grack02 = 'genericuser@grack02.uvic.trans-cloud.net'
grack01 = 'genericuser@grack01.uvic.trans-cloud.net'
sebulba = 'cmatthew@sebulba.cs.uvic.ca'

uvic_cluster =  [sebulba,grack06,grack05,grack04,grack03,grack02,grack01]


# emu1='cmatthew@pc283.emulab.net'
# emu2='cmatthew@pc320.emulab.net'
# emu3='cmatthew@pc297.emulab.net'
# emu4='cmatthew@pc303.emulab.net'
emu1='cmatthew@pc324.emulab.net'
emu2='cmatthew@pc280.emulab.net'
emu3='cmatthew@pc288.emulab.net'
emu4='cmatthew@pc311.emulab.net'

emulab_cluster =  [emu1, emu2, emu3, emu4]

nw1 = "cmatthew@pc2.instageni.northwestern.edu"
nw2 = "cmatthew@pc3.instageni.northwestern.edu"
nw3 = "cmatthew@pc4.instageni.northwestern.edu"
nw4 = "cmatthew@pc5.instageni.northwestern.edu"

nw_cluster = [nw2, nw3, nw4]

usp1 = "cmatthew@pc23.emulab.larc.usp.br"
#usp2 = "cmatthew@pc22.emulab.larc.usp.br"
usp3 = "cmatthew@pc21.emulab.larc.usp.br"
usp4 = "cmatthew@pc20.emulab.larc.usp.br"
usp5 = "cmatthew@pc24.emulab.larc.usp.br"

usp_cluster = [usp1,  usp3, usp4, usp5]

jp1 = "root@192.168.251.10"

jp_cluster = [jp1]

ks1 = "toor@glab035.e4.ukl.german-lab.de"
ks2 = "toor@glab037.e4.ukl.german-lab.de"
ks3 = "toor@glab038.e4.ukl.german-lab.de"

ks_cluster = [ks1, ks2, ks3]


all_clusters = [brussels_cluster, uvic_cluster, emulab_cluster, nw_cluster, jp_cluster, usp_cluster] 

# tmp dirs are different at different clusters. 
tmp_dirs = {"cs.UVic.CA":"/tmp/",
            "uvic.trans-cloud.net":"/tmp/",
            "emulab.net":"/mnt/",
            ".ibbt.be":"/mnt/",
            "northwestern.edu":"/mnt/",
            "u-tokyo.ac.jp":"/data/",
            "usp.br":"/mnt/",
            "german-lab.de":"/tmp/",
            "undefined.location":'/tmp/'}

user_ids = {"cs.UVic.CA":"gis",
            "uvic.trans-cloud.net":"gis6",
            "emulab.net":"gis1",
            ".ibbt.be":"gis",
            "northwestern.edu":"gis",
            "u-tokyo.ac.jp":"gis4",
            "usp.br":"gis2",
            "german-lab.de":"gis",
            "undefined.location":'gis'}

swift_proxies = {"cs.UVic.CA":"165.124.51.144",
            "uvic.trans-cloud.net":"10.10.6.3",
            "emulab.net":"10.10.1.3",
            ".ibbt.be":"165.124.51.144",
            "northwestern.edu":"10.10.1.3",
            "u-tokyo.ac.jp":"10.10.4.3",
            "usp.br":"10.10.2.3",
            "german-lab.de":"165.124.51.144",
            "undefined.location":'165.124.51.144'}


class Cluster(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


    def validate(self):
        for prop in ['lat','lon', 'shortname', 'tmpdir', 'swiftproxys','fallbackswift' 'machines', 'baseip']:
            assert prop in self.__dict__, "Cluster is missing "+prop 

uvic_swift1 = '142.104.195.225'
uvic_swift2 = '142.104.195.226'
nw_swift1 = 'pc5.instageni.northwestern.edu'


uvic = Cluster(   lat="48.4633",
                         lon="123.3118",
                         shortname="uvic",
                         tmpdir="/tmp/",
                         swiftproxys=[uvic_swift1, uvic_swift2],
                         fallbackswiftmachines=[nw_swift1],
                         baseip="142.104")


def n_machines():
    """How many machines are there?"""
    n = 0
    for cluster in all_clusters:
        for machine in cluster:
            n += 1
    return n


def test_getclusters():
    assert n_machines() > 0, "Where are the machines?" 


import sys
sys.path.insert(0, './mq/')
import taskmanager
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
    assert get_cluster_user_id() in ['system:gis', 'system:gis1', 'system:gis2', 'system:gis3', 'system:gis4',
                                     'system:gis6']

def get_cluster_swift_proxy():
    cluster_name = taskmanager.get_local_site_name()
    assert cluster_name in swift_proxies, "%s not in swift_proxies" % cluster_name
    return  swift_proxies[cluster_name]

    
def test_swift_proxy():
    assert get_cluster_swift_proxy() in ['165.124.51.144', '10.10.1.3', '10.10.2.3', '10.10.3.3', '10.10.4.3', '10.10.5.3', '10.10.6.3']


def test_clusters():
    uvic.validate()
