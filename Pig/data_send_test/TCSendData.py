'''
Created on 2011-03-09

@author: cmatthew
'''



import httplib, urllib
import datetime
hostname = "127.0.0.1:8000"

# site, startTime, nodes, size, description=None
def send_new_job(name, site, startTime, nodes, size, description):
  params = {'name': name, 
            'site': site, 
            'startTime': startTime, 
            'nodes':nodes, 
            'size':size, 
            'description':description}
  http_send("/jobs/api/add_hadoop/",params)


def update_job_status(job, elapsed_time ,percent):
  params = {'name': job,
            'timeInSec': elapsed_time,
            'percent':percent}
  http_send("/jobs/api/update_hadoop/",params)

  
def finish_job(job, elapsed_time):
  params = {'name': job,
            'timeInSec': elapsed_time}
  http_send("/jobs/api/finish_hadoop/",params)


def http_send(interface, params):
    """Send this params dict to the interface on transcloud"""
    params = urllib.urlencode(params)
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
    conn = httplib.HTTPConnection(hostname)
    conn.request("POST",interface, params, headers)
    response = conn.getresponse()

    if response.status != 200:
      print "Problem making http request to server: code %d message: %s"%(response.status, response.reason)
    data = response.read()
    print "web: ", data
    conn.close()


if __name__ == '__main__':
    jobname = "Foodoop"
    send_new_job(jobname, "UVic", datetime.datetime.now(), "800", "123456", "Oink...")
    update_job_status(jobname, datetime.datetime.now(), "10")
    update_job_status(jobname, datetime.datetime.now(), "60")
    update_job_status(jobname, datetime.datetime.now(), "80")
    update_job_status(jobname, datetime.datetime.now(), "100")
    finish_job(jobname, datetime.datetime.now())
    