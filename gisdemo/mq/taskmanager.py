import mq
import json
import socket
import sys
import time

_sites={0:"undefined.location", 1:"cs.UVic.CA", 2:"emulab.net", 3:".ibbt.be",4:"northwestern.edu", 5:"u-tokyo.ac.jp", 6:"usp.br", 7:"german-lab.de"}

_ip_to_site={'142.104':_sites[1], '155.98':_sites[2], '10.2':_sites[3], '165.124':_sites[4], '192.168':_sites[5], '200.144':_sites[6],'131.246':_sites[7] }

_decided_site_name = None

def  get_local_site_name():
    """Try and decide which cluster this machine is running in
    I do this by checking the IP address and take the first digits
    and deduce the cluster from that.

    Cache results so that we don't have to connect a bunch of times.
    """
    global _decided_site_name

    # Have we dont this before?
    if _decided_site_name != None:
        return _decided_site_name

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("python.org",80))
        ip = s.getsockname()[0]
        s.close()
    except Exception as e:
        print "Failed to connect to python.org -- sleeping and trying again."
        time.sleep(10)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("python.org",80))
        ip = s.getsockname()[0]
        s.close()

    front = ip.split(".")[0:2]
    front = '.'.join(front)
    if front not in _ip_to_site:
        print "Warning: running from an undefined cluster."
        site_name = "undefined.location"
    else:
        site_name = _ip_to_site[front]

    _decided_site_name = site_name
    
    return site_name


def test_getsitename():
    print "get sitename"
    site = get_local_site_name()
    assert site != "", "sitename missing: %s"%(site)
    assert len(site) > 4, "site name very short!"
    assert "." in site, "Site must have at least one dot/"
    assert site in _sites.values(), "Site name was not in our list!"


def get_queue_name(site):
    return _sites[site]


def get_site_num(name):
    for num, site_name in _sites.iteritems():
        if name == site_name:
            return num
    assert False, "Tried to access a site name which does not exist."


class TaskManager():
    """Task Manager is an abstraction on top of message
    queues.  It allows tasks to be set to all the clusters.
    Task clients can then pick up cluster specific messages.
    Task manager also supports one results queue to send
    messages back.
    """
    def __init__(self,prefix=""):
        mq.setup()
        self.test_prefix = prefix
        
    def add_task(self, jobobj, site=None):
        site = self._get_site(site)
        mq.push_job( json.dumps(jobobj), self.myqueue(site), 60*25)

    def clear(self, site):
        site = self._get_site(site)
        mq.clear_queue( self.myqueue(site))

    def myqueue(self,site=None):
        site=self._get_site(site)
        return self.test_prefix + get_queue_name(site)

    def reset(self):
        for key, value in _sites.iteritems():
            self.clear(key)
        mq.clear_queue( self.test_prefix+RESULT_QUEUE_NAME)

    def _get_site(self, site):
        if site == None:
            site =  get_site_num(get_local_site_name())
        assert site in _sites, "Site not in sites list"
        return site
    
    def get_size(self, site=None):
        site=self._get_site(site)
        return mq.sizeof(self.myqueue(site))


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
    
    def get_size(self):
        return mq.sizeof(self.queuename())


    def blocking_get_task(self, testing=False, threshold=640):
        assert False, "This is buggy. Ut shoud not be used."
        delay = 10
        new_job = None
        jobid = None
        
        while(True):
            new_job, jobid = self.get_task() if not testing else (None,None)
            print testing, new_job
            if new_job == None:
                print '.',
                sys.stdout.flush()
                if delay > threshold:
                    return None
                time.sleep(delay)
                delay *= 2
                continue

        return new_job, jobid


    def report_done(self, jobid, result=None):
        mq.done(self.queue, jobid)

        if result != None:
            assert self.queue != RESULT_QUEUE_NAME, "Putting a message on the done queue is not allowed!"
            result_str = json.dumps(result)
            mq.push_job(result_str, self.prefix+RESULT_QUEUE_NAME, timeout=60)


def test_TaskManager():
    tm = TaskManager(prefix="testing_")
    tm.reset()
    # Push in three jobs and test

    job = {'task': 'greencities', 'city': 1}
    job2 = {'task': 'greencities', 'city': 2}
    job3 = {'task': 'greencities', 'city': 3}
    tm.add_task(job)
    tm.add_task(job2)
    tm.add_task(job3)

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

    # t1 = time.time()
    # #r = result_client.blocking_get_task(testing=True)
    # t2 = time.time()

    # assert 69 <= t2-t1 <= 71, "Blocking test should die after 10+20+40 seconds."
    # assert r == None, "Was not expecting something back."
