import mq
import json
import socket
import sys
import time

_sites={1:"cs.UVic.CA", 2:"uvic.trans-cloud.net"}

_ip_to_site={'142.104':_sites[1]}

def  get_local_site_name():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("python.org",80))

    ip = s.getsockname()[0]

    s.close()
    front = ip.split(".")[0:2]
    front = '.'.join(front)
 
    str = _ip_to_site[front]
    
    return str

def test_getsitename():
    site = get_local_site_name()
    assert site != "", "sitename missing: %s"%(site)
    assert len(site) > 4, "site name very short!"
    assert "." in site, "Site must have at least one dot/"
    assert site in _sites.values(), "Site name was not in our list!"

def get_queue_name(site):
    return _sites[site]


class TaskManager():
    def __init__(self,prefix=""):
        mq.setup()
        self.test_prefix = prefix
        
    def add_task(self, jobobj, site):
        assert site in _sites, "Site not in sites list"
        mq.push_job( json.dumps(jobobj), self.myqueue(site))

    def clear(self, site):
        mq.clear_queue( self.myqueue(site))

    def myqueue(self,site):
        return self.test_prefix + get_queue_name(site)

    def reset(self):
        for key, value in _sites.iteritems():
            self.clear(key)
        mq.clear_queue( self.test_prefix+RESULT_QUEUE_NAME)


RESULT_QUEUE_NAME="global_results_queue"

class TaskClient():
    def __init__(self, queue=get_local_site_name(),prefix=""):
        mq.setup()
        self.prefix=prefix
        self.queue = prefix+queue

    def queuename(self):
        print self.queue
        return self.queue

    def get_task(self):
        jobstr, jobid = mq.get_job(self.queuename())
        if jobstr == None:
            return None, None
        task = json.loads(jobstr)
        return task, jobid

    def blocking_get_task(self):
        delay = 1
        new_job = None
        jobid = None
        while(True):
            new_job, jobid = self.get_task()
            if new_job == None:
                print '.',
                sys.stdout.flush()
                time.sleep(delay%120)
                delay *= 2
                continue

        return new_job, jobid


    def report_done(self, jobid, result=None):
        mq.done(self.queue, jobid)

        if result != None:
            assert self.queue != RESULT_QUEUE_NAME, "Putting a message on the done queue is not allowed!"
            result_str = json.dumps(result)
            mq.push_job(result_str, self.prefix+RESULT_QUEUE_NAME)

def test_TaskManager():
    tm = TaskManager(prefix="testing_")
    tm.reset()
    # Push in three jobs and test

    job = {'task': 'greencities', 'city':1}
    job2 = {'task': 'greencities', 'city':2}
    job3 = {'task': 'greencities', 'city':3}
    tm.add_task(job,1)
    tm.add_task(job2,1)
    tm.add_task(job3,1)

    time.sleep(1)
    remote_client = TaskClient(prefix="testing_")

    result_client = TaskClient(queue=RESULT_QUEUE_NAME, prefix="testing_")

    # check the jobs are there
    new_job, jobid = remote_client.get_task()
    assert new_job != None, "get task should be returning values!"
    assert new_job['task'] == job['task'], "Task1 did not match."
    assert new_job['city'] == job['city'], "Task1 city did not match."
    remote_client.report_done(jobid, {'task':'greencities', 'result':[0.5]})

    new_job, jobid = remote_client.get_task()
    assert new_job != None, "get task should be returning values!"
    assert new_job['task'] == job2['task'], "Task2 did not match."
    assert new_job['city'] == job2['city'], "Task2 city did not match."
    remote_client.report_done(jobid, {'task':'greencities', 'result':[0.6]})

    new_job, jobid = remote_client.get_task()
    assert new_job != None, "get task should be returning values!"
    assert new_job['task'] == job3['task'], "Task3 did not match."
    assert new_job['city'] == job3['city'], "Task3 city did not match."
    remote_client.report_done(jobid, {'task':'greencities', 'result':[0.7]})

    time.sleep(1)

    # Now check the results came in
    new_result, resultid = result_client.get_task()

    assert new_result['task'] == 'greencities', "Task missing in result"
    assert new_result['result'][0] == 0.5, "Results missing in result message"
    result_client.report_done(resultid)
    
    new_result, resultid = result_client.get_task()
    assert new_result['task'] == 'greencities', "Task missing in result"
    assert new_result['result'][0] == 0.6, "Results2 missing in result message"
    result_client.report_done(resultid)

    new_result, resultid = result_client.get_task()
    assert new_result['task'] == 'greencities', "Task missing in result"
    assert new_result['result'][0] == 0.7, "Results3 missing in result message"
    result_client.report_done(resultid)


    

