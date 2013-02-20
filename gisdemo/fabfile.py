from fabric.api import *
from fabric.contrib.console import confirm
import os

env.use_ssh_config=True

here = os.path.realpath(__file__)

ZIPFILE= 'my_project.tar.gz'

env.roledefs = {
    #    'uvic': ['sebulba.cs.uvic.ca','genericuser@grack06.uvic.trans-cloud.net'],
    'uvic': [ 'cmatthew@sebulba.cs.uvic.ca','genericuser@grack06.uvic.trans-cloud.net','genericuser@grack05.uvic.trans-cloud.net'],
    'northwestern': [],
    'test':['genericuser@grack06.uvic.trans-cloud.net'],
    'sebulba':[ 'cmatthew@sebulba.cs.uvic.ca']
}

env.passwords = {'genericuser@grack06.uvic.trans-cloud.net':'cleb020',
                 'genericuser@grack05.uvic.trans-cloud.net':'cleb020',
                 'sebulba.cs.uvic.ca':'enec869'}

testable_files = "combine.py mq/mq.py mq/taskmanager.py mq_test.py dbObj.py gcswift.py"

def test():
    local("py.test "+testable_files)

def pack():
    with settings(warn_only=True):
        local('find . -name "*.pyc" -exec rm -rf {} \;')
        local('find . -name "__pycache__" -exec rm -rf {} \;')
        local('rm -rf green.log')
    local('rm -rf /tmp/'+ZIPFILE)
    local('tar czf /tmp/'+ZIPFILE+' .')

# where to install on the remote machine
deploy_path='/usr/local/src/greencities/'


@roles('uvic')
def deploy():
    pack()
    put('/tmp/'+ZIPFILE, '/tmp/')
    sudo('rm -rf '+deploy_path)
    sudo('mkdir '+deploy_path)
    sudo('chmod -R 777 '+deploy_path)
    with cd(deploy_path):
        sudo('tar xzf /tmp/'+ZIPFILE)


@roles('test')
def test_everywhere():
    pack()
    deploy()
    with cd(deploy_path):
        run('py.test '+ testable_files)


@roles('test')
def install_deps():
    with settings(warn_only=True):
        sudo('apt-get update')
    sudo('apt-get -y --force-yes install python-pip python-dev python-py libpq-dev build-essential python-numpy python-numpy-dev python-scipy proj')
    pkgs = ['pypng','pytest','python-swiftclient','iron-mq', 'psycopg2']
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
        sudo('ldconfig')
        

@roles('test')
def run_start():
    deploy()
    with cd(deploy_path):
        run('python mq_calc.py -c 15')
        


@roles('test')
def run_workers():
    deploy()
    with cd(deploy_path):
        run('python mq_client.py')

@roles('test')
def run_results():
    deploy()
    with cd(deploy_path):
        with settings(warn_only=True):
            sudo('rm -rf green.log')
        run('python mq_process_results.py')



@hosts('sebulba')
def update_to_swift():
        with cd(deploy_path):
            run('python send_swift_images.py')
