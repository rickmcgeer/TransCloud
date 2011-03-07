import os, sys
CLOUDBOARD_ROOT = '/usr/local/django/cloudboard'
sys.path.append(CLOUDBOARD_ROOT)
sys.path.append(CLOUDBOARD_ROOT +'/cloudboard')
os.environ['DJANGO_SETTINGS_MODULE'] = 'cloudboard.settings'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
