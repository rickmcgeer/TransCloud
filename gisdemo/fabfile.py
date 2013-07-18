from fabric.api import *
from fabric.contrib.console import confirm
from fabric.contrib.files import exists
from fabric.utils import abort

import os
import time
from clusters import *
env.use_ssh_config=False

here = os.path.dirname(os.path.realpath(__file__))

ZIPFILE= 'my_project.tar.gz'

env.roledefs = {
    #'brussels':brussels_cluster,
    #'ks':ks_cluster,
    'uvic':uvic_cluster,
    #'nw':nw_cluster,
    #'usp':usp_cluster,
    #'emulab':emulab_cluster,
    'server':[grack06],
    'db_server':[grack06],
    'web_server':[grack06],
    'workers':uvic_cluster,
    #'jp-relay':["shu@pc229.emulab.net"],
}

env.key_filename = here+'/transgeo'

env.disable_known_hosts = True

env.passwords = {grack06:'cleb020',
                 grack04:'cleb020',
                 grack03:'cleb020',
                 grack02:'cleb020',
                 grack01:'cleb020',
}

testable_files = "clusters.py combine.py mq/mq.py mq/taskmanager.py mq_test.py dbObj.py gcswift.py greenspace.py "
#testable_files = "greenspace.py"

@roles(['workers', 'server'])
def killall():
    """stop python processes everywhere."""
    with settings(warn_only=True):
        sudo("killall python")

def test():
    local("py.test "+testable_files)


# @roles('nw')
# def disk_space():
#     with settings(warn_only=True):
#         run('df -h')
#     sudo('chmod -R 777 /mnt/')

def style():
    local('pep8 *.py ./mq/*.py')
    local('pylint *.py ./mq/*.py')

@runs_once
def pack():
    with settings(warn_only=True):
        local('find . -name "*.pyc" -exec rm -rf {} \;')
        local('find . -name "__pycache__" -exec rm -rf {} \;')
        local('rm -rf green.log')
    local('rm -rf /tmp/'+ZIPFILE)
    local('tar czf /tmp/'+ZIPFILE+' \'--exclude=clean_world.sql.bz2\'  .')


@roles('brussels')
def route():
    with settings(warn_only=True):
        sudo('/share/nat.sh')


# where to install on the remote machine
deploy_path='/usr/local/src/greencities/'

def deploy():
    pack()
    put('/tmp/'+ZIPFILE, '/tmp/')
    sudo('rm -rf '+deploy_path)
    sudo('mkdir '+deploy_path)
    sudo('chmod -R 777 '+deploy_path)
    with cd(deploy_path):
        sudo('tar xzf /tmp/'+ZIPFILE)
    sudo('chmod -R 777 '+deploy_path)


@roles('uvic')
def test_everywhere():
    execute(check_lock)
    pack()
    deploy()
    with cd(deploy_path):
        run('py.test -s '+ testable_files)
    execute(remove_lock)

@roles('workers')
def clean_up_gdal():
    with cd('gdal-1.9.1'):
        run('make clean')

@parallel
@roles('workers')
def clean_up_tmps():
    with cd('/tmp/'):
        sudo('rm -rf landsat*')
        sudo('rm -rf p*')
        sudo('rm -rf *.tif')
        sudo('rm -rf *.png*')
        sudo('rm -rf *.dbf')
        sudo('rm -rf *.shp')
        sudo('rm -rf *.shx')
        sudo('rm -rf green.log')
        sudo('rm -rf tmp*')
        sudo('rm -rf swift_file_cache')
        
    with cd('/mnt/'):
        sudo('rm -rf landsat*')
        sudo('rm -rf p*')
        sudo('rm -rf *.tif')
        sudo('rm -rf *.png*')
        sudo('rm -rf *.dbf')
        sudo('rm -rf *.shp')
        sudo('rm -rf *.shx')
        sudo('rm -rf green.log')
        sudo('rm -rf tmp*')
        sudo('rm -rf swift_file_cache')

@parallel
@roles('workers')
def install_deps():
    with settings(warn_only=True):
        sudo('apt-get update')
    sudo('apt-get -y --force-yes install python-pip python-dev libpq-dev build-essential python-numpy python-numpy-dev python-scipy proj')
    pkgs = ['pypng','pytest','python-swiftclient','iron-mq', 'psycopg2','py']
    sudo('pip install --upgrade pip')
    sudo('pip install --upgrade virtualenv')
    for pkg in pkgs:
        sudo('pip install '+pkg)
    run('wget http://download.osgeo.org/gdal/gdal-1.9.1.tar.gz')
    run('tar zxf gdal-1.9.1.tar.gz')
    with cd('gdal-1.9.1'):
        run('./configure --with-python --prefix=/usr/local')
        run('make -j8 all')
        sudo('make install')
        run('make clean')
        sudo('ldconfig')

@roles('db_server')
def server_deploy():
    database = 'world'
    with settings(warn_only=True):
        sudo('createdb ' + database, user="postgres")
        sudo('createuser -s -r -d root', user='postgres')
        sudo('createuser -S -R -D www-data', user='postgres')
        sudo('createuser -S -R -D -P uvicgis gis', user='postgres')
        sudo('psql ' + database + ' -f ' + deploy_path +'/clean_world.sql', user='postgres')

@runs_once
def make_lockfile():
	local("hostname > lockfile")
	local("date >> lockfile")
	local("cat lockfile")


@roles('server')
def check_lock():
	make_lockfile()
	if exists("/tmp/lockfile", use_sudo=False, verbose=True):
		run("cat /tmp/lockfile")
		abort("The experiment is locked, talk to the locker or delete the lockfile")	
	else:
		put("lockfile", "/tmp/lockfile")

@roles('server')
def remove_lock():
	run("rm -rf /tmp/lockfile")
        
@roles('web_server')
def web_server_deploy():
    with settings(warn_only=True):
        geoserver_web_dir = "/usr/share/opengeo-suite-data/geoserver_data/www/"
        map_dir = geoserver_web_dir + "maps"
        recipe_data_dir = "/usr/share/opengeo-suite/recipes/resources/openlayers/examples/data"
        recipe_theme_dir = "/usr/share/opengeo-suite/recipes/resources/openlayers/theme"
        sudo('apt-get -y --force-yes install apache2')
        sudo("mkdir " +  map_dir)
        # sudo("cp -r " + geoserver_web_dir + "openlayers/* " + map_dir)
        sudo("cp -r " + recipe_data_dir + " " + map_dir)
        sudo("wget http://openlayers.org/api/OpenLayers.js -O " + map_dir + "/OpenLayers.js")
        sudo("cp " + deploy_path + "maps/view.html " + map_dir)
        sudo("chown www-data " + map_dir +"/view.html")
        sudo("cp " + deploy_path + "httpd.conf /etc/apache2/httpd.conf" )
        sudo("cp /etc/apache2/mods-available/headers.load /etc/apache2/mods-enabled")
        sudo("cp " + deploy_path + "headers.conf /etc/apache2/mods-enabled")
        sudo("apache2ctl restart")


@roles('server')
def run_start(ncities='10'):
    """Run the calculation on ncities*clusters cities.
    Lock the calculation, then load the cities from database and
    put them in the message queues.

    Should only need to be run once per run.
    """
    execute(check_lock)
    deploy()
    with cd(deploy_path):
        run('python mq_calc.py -c '+ncities)

            

@roles('workers')
@parallel
def run_workers():
    with settings(warn_only=True):
	    sudo('chmod 777 /mnt/') # These seem to be set wrong once and a while. Set it back
    deploy()
    with cd(deploy_path):
        with settings(warn_only=True):
            run('python mq_client.py')


@roles('server')
def run_results():
    deploy()
    with cd(deploy_path):
	print "Having a quick nap while we wait for messages to arrive in the queues"
	time.sleep(60) # It seems results are not always in the queue when we start right after
        run('python mq_process_results.py')
        
    execute(remove_lock)


# @hosts('sebulba')
# def update_to_swift():
# 	assert False, "Not used."
#         with cd(deploy_path):
#             run('python send_swift_images.py')


# @roles('jp-relay')
# def deploy_jp():
#     """Japan is a special case which needs a relay."""
#     deploy()
#     with cd(deploy_path):
#         #root@192.168.251.10
#         run('scp -vv /tmp/my_project.tar.gz root@192.168.251.10:/tmp/my_project.tar.gz')


# @hosts('root@192.168.251.10')
# def deploy_jp_node():
#     """this script gets copied to relay, then this function gets executed there."""
#     deploy()
#     with cd(deploy_path):
#             run('python mq_client.py')
    

def all(ncities=10):

    execute(run_start, ncities)
    execute(run_workers)
    execute(run_results)

