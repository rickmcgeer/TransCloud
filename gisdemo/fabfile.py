from fabric.api import *
from fabric.contrib.console import confirm
import os
from clusters import *
env.use_ssh_config=True

here = os.path.dirname(os.path.realpath(__file__))

ZIPFILE= 'my_project.tar.gz'

env.roledefs = {
    'brussels':brussels_cluster,
    'uvic':uvic_cluster,
    'emulab':emulab_cluster,
    'server':[grack06],
    'workers':uvic_cluster + emulab_cluster + brussels_cluster,

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
                 br03:''}

testable_files = "clusters.py combine.py mq/mq.py mq/taskmanager.py mq_test.py dbObj.py gcswift.py greenspace.py "


def test():
    local("py.test "+testable_files)


@roles('brussels')
def disk_space():
    with settings(warn_only=True):
        run('df -h')
    sudo('chmod -R 777 /mnt/')

def style():
    local('pep8 *.py ./mq/*.py')
    local('pylint *.py ./mq/*.py')

def pack():
    with settings(warn_only=True):
        local('find . -name "*.pyc" -exec rm -rf {} \;')
        local('find . -name "__pycache__" -exec rm -rf {} \;')
        local('rm -rf green.log')
    local('rm -rf /tmp/'+ZIPFILE)
    local('tar czf /tmp/'+ZIPFILE+' .')

# where to install on the remote machine
deploy_path='/usr/local/src/greencities/'


@roles('brussels')
def route():
    with settings(warn_only=True):
        sudo('/share/nat.sh')


@roles('uvic')
def deploy():
    pack()
    put('/tmp/'+ZIPFILE, '/tmp/')
    sudo('rm -rf '+deploy_path)
    sudo('mkdir '+deploy_path)
    sudo('chmod -R 777 '+deploy_path)
    with cd(deploy_path):
        sudo('tar xzf /tmp/'+ZIPFILE)
    sudo('chmod -R 777 '+deploy_path)

@hosts(sebulba)
#@roles('brussels')
def test_everywhere():
    pack()
    deploy()
    with cd(deploy_path):
        run('py.test '+ testable_files)

@roles('workers')
def clean_up_gdal():
    with cd('gdal-1.9.1'):
        run('make clean')

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

@roles('server')
def run_start():
    deploy()
    with cd(deploy_path):
        run('python mq_calc.py -c 500')
#@hosts([br01])

@parallel
@roles('workers')
def run_workers():
    deploy()
    with cd(deploy_path):
        run('python mq_client.py')

@roles('server')
def run_results():
    deploy()
    with cd(deploy_path):
        with settings(warn_only=True):
            sudo('rm -rf green.log')
        run('python mq_process_results.py')
        run('echo Errors')
        run('cat /tmp/error.log')

@hosts('sebulba')
def update_to_swift():
        with cd(deploy_path):
            run('python send_swift_images.py')

def all():
    execute(run_start)
    execute(run_workers)
    execute(run_results)
