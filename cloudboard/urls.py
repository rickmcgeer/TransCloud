from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', 'jobs.views.index'),
    (r'^jobs/$', 'jobs.views.index'),
    (r'^jobs/developer/$', 'jobs.views.developer'),
    (r'^jobs/developer/add/$', 'jobs.views.developerAdd'),
    (r'^jobs/developer/batchAdd/$', 'jobs.views.developerBatchAdd'),
    (r'^jobs/developer/cleanup/$', 'jobs.views.developerCleanup'),
    (r'^jobs/developer/close.*$', 'jobs.views.developerClose'),
    (r'^jobs/developer/errorResult.*$', 'jobs.views.developerErrorResult'),
    (r'^jobs/developer/addForm/$', 'jobs.views.addForm'),
    (r'^jobs/api/add_hadoop/$', 'jobs.views.api_submit_new_hadoop_job'),
    (r'^jobs/api/update_hadoop/$', 'jobs.views.api_update_hadoop_job'),
    (r'^jobs/api/finish_hadoop/$', 'jobs.views.api_finish_hadoop_job'),
    (r'^jobs/add/$', 'jobs.views.add'),                   
    (r'^jobs/close.*$', 'jobs.views.close'),
    (r'^jobs/errorResult.*$', 'jobs.views.errorResult'),
    (r'^jobs/site/(?P<siteName>\w+)/', 'jobs.views.siteDetail'),
    (r'^site/(?P<siteName>\w+)/', 'jobs.views.siteDetail'),
    (r'^summaryStats/$', 'jobs.views.summaryStats')

    # (r'^admin/', include(admin.site.urls)),
)
