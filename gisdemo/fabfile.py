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

testable_files = "combine.py mq/mq.py mq/taskmanager.py mq_test.py dbObj.py"

def test():
    local("py.test "+testable_files)

def pack():
    local('find . -name "*.pyc" -exec rm -rf {} \;')
    local('find . -name "__pycache__" -exec rm -rf {} \;')
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
        run('py.test '+ testable_files)


@roles('uvic')
def install_deps():
    with settings(warn_only=True):
        sudo('apt-get update')
    sudo('apt-get -y install python-pip python-dev python-py libpq-dev')
    pkgs = ['pypng','pytest','python-swiftclient','iron-mq', 'psycopg2']
    sudo('pip install --upgrade pip')
    sudo('pip install --upgrade virtualenv')
    for pkg in pkgs:
        sudo('pip install '+pkg)


@roles('test')
def run_workers():
    with cd(deploy_path):
        run('python mq_calc.py -c 15')
        run('python mq_client.py')

@hosts('sebulba')
def update_to_swift():
        with cd(deploy_path):
            run('python send_swift_images.py')
