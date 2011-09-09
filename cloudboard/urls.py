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
    (r'^jobs/developer/enterHadoopJob/$', 'jobs.views.enterHadoopForm'),
    (r'^jobs/api/add_hadoop/$', 'jobs.views.api_submit_new_hadoop_job'),
    (r'^jobs/api/update_hadoop/$', 'jobs.views.api_update_hadoop_job'),
    (r'^jobs/api/finish_hadoop/$', 'jobs.views.api_finish_hadoop_job'),
    (r'^jobs/add/$', 'jobs.views.add'),                   
    (r'^jobs/close.*$', 'jobs.views.close'),
    (r'^jobs/errorResult.*$', 'jobs.views.errorResult'),
    (r'^jobs/site/(?P<siteName>\w+)/', 'jobs.views.siteDetail'),
    (r'^site/(?P<siteName>\w+)/', 'jobs.views.siteDetail'),
    (r'^summaryStats/$', 'jobs.views.summaryStats'),
    (r'^cluster_info/$', 'jobs.views.clusterInfo'),
    (r'^cluster_switch/$', 'jobs.views.clusterSwitch'),
    (r'^cluster_switch_status/$', 'jobs.views.clusterSwitchStatus'),
    (r'^hadoop/$', 'jobs.views.hadoopJobTable'),
    (r'^hadoop/site/(?P<siteName>\w+)/', 'jobs.views.hadoopSiteTable'),
    (r'^jobs/api/add_hadoop_result/$', 'jobs.views.api_submit_new_hadoop_result'),
    (r'^jobs/api/add_batch_hadoop_result/$', 'jobs.views.api_batch_hadoop_result'),
    (r'^jobs/developer/enterHadoopResult/$', 'jobs.views.enterHadoopResultForm'),
    (r'^jobs/api/cleanupDatabase/$', 'jobs.views.api_clean_db'), #should be done from the admin interface
                       
                       
                      


     (r'^admin/', include(admin.site.urls)),
)
