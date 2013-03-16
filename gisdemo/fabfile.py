from fabric.api import *
from fabric.contrib.console import confirm
import os
import time
from clusters import *
env.use_ssh_config=False

here = os.path.dirname(os.path.realpath(__file__))

ZIPFILE= 'my_project.tar.gz'

env.roledefs = {
    'brussels':brussels_cluster,
    'ks':ks_cluster,
    'uvic':uvic_cluster,
    'nw':nw_cluster,
    'usp':usp_cluster,
    'emulab':emulab_cluster,
    'server':[sebulba],
    'db_server':[nw1],
    'web_server':[nw1],
    'workers':uvic_cluster + emulab_cluster + brussels_cluster + nw_cluster + usp_cluster + ks_cluster,
    'jp-relay':["root@pc515.emulab.net"],
    'sebulba':[sebulba]
}

env.key_filename = here+'/transgeo'

env.passwords = {grack06:'cleb020',
                 grack05:'cleb020',
                 grack04:'cleb020',
                 grack03:'cleb020',
                 grack02:'cleb020',
                 grack01:'cleb020',
                 sebulba:'enec869',
                 br01:'',
                 br02:'',
                 br03:'',
                 ks1:'gr33nc!ty',
                 ks2:'gr33nc!ty',
                 ks3:'gr33nc!ty'}

testable_files = "clusters.py combine.py mq/mq.py mq/taskmanager.py mq_test.py dbObj.py gcswift.py greenspace.py "

@roles(['workers', 'server'])
def killall():
    """stop python processes everywhere."""
    with settings(warn_only=True):
        sudo("killall python")

def test():
    local("py.test "+testable_files)


@roles('nw')
def disk_space():
    with settings(warn_only=True):
        run('df -h')
    sudo('chmod -R 777 /mnt/')

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

# where to install on the remote machine
deploy_path='/usr/local/src/greencities/'


@roles('brussels')
def route():
    with settings(warn_only=True):
        sudo('/share/nat.sh')



def deploy():
    pack()
    put('/tmp/'+ZIPFILE, '/tmp/')
    sudo('rm -rf '+deploy_path)
    sudo('mkdir '+deploy_path)
    sudo('chmod -R 777 '+deploy_path)
    with cd(deploy_path):
        sudo('tar xzf /tmp/'+ZIPFILE)
    sudo('chmod -R 777 '+deploy_path)

#@hosts([ks])
@roles('nw')
def test_everywhere():
    pack()
    deploy()
    with cd(deploy_path):
        run('py.test -s '+ testable_files)

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
@roles('emulab')
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
def run_start():
    deploy()
    with settings(warn_only=True):
        # the daemon pid file, to make sure it does not linger
        # from a previous run.
        run('rm -rf /tmp/daemon-calc.pid') 
        run('rm -rf /tmp/calc_daemon.log')
    with cd(deploy_path):
        run('python mq_calc.py -c 1')
	# with settings(warn_only=True):
		#sudo('rm -rf green.log')
	    #run('python calc_daemon.py start')

        
@parallel
@roles('workers')
def run_workers():
    deploy()
    with cd(deploy_path):
        with settings(warn_only=True):
            run('python mq_client.py')


@roles('server')
def run_results():
    deploy()
    with cd(deploy_path):
        run('python mq_process_results.py')
        get('/tmp/calc_daemon.log', 'calc_daemon.log')
        

@hosts('sebulba')
def update_to_swift():
        with cd(deploy_path):
            run('python send_swift_images.py')


@roles('jp-relay')
def deploy_jp():
    deploy()
    with cd(deploy_path):
            run('fab deploy_jp_node')


@hosts('root@192.168.251.10')
def deploy_jp_node():
    deploy()
    with cd(deploy_path):
            run('python mq_client.py')
    

def all():
    execute(run_start)
    execute(run_workers)
    execute(run_results)
