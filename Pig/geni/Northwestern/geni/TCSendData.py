'''
Created on 2011-03-09

@author: cmatthew
'''



import httplib, urllib
import datetime
hostname = "trans-cloud.net"

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

def logPrint(fileObj, strToPrint):
    if fileObj:
	print >> fileObj, strToPrint
    else: print strToPrint

def http_send(interface, params, logFile="TCSendDataLog.log"):
    """Send this params dict to the interface on transcloud"""
    if logFile: fileObj = open(logFile, 'a')
    logPrint(fileObj, "#*** NEW REQUEST")
    logPrint(fileObj, 'params = {')
    for param in params.keys():
        logPrint(fileObj, "    '%s' : '%s'," % (param, params[param]))
    logPrint(fileObj, "}")
    logPrint(fileObj, 'request = ' + interface)
    logPrint(fileObj, "#*** END REQUEST")

    params = urllib.urlencode(params)
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
    conn = httplib.HTTPConnection(hostname)
    print("*************" + str(hostname) + " " + str(interface) + " " + str(params) + " " + str(headers))
    conn.request("POST",interface, params, headers)
    response = conn.getresponse()

    if response.status != 200:
      logPrint(fileObj, "Problem making http request to server: code %d message: %s"%(response.status, response.reason))
    data = response.read()
    logPrint(fileObj, "web: " +  data)
    conn.close()
    if fileObj: fileObj.close()



if __name__ == '__main__':
    jobname = "Foodoop"
    send_new_job(jobname, "UVic", datetime.datetime.now(), "800", "123456", "Oink...")
    time =  datetime.datetime.now().second
    update_job_status(jobname, time, "10")
    update_job_status(jobname, time, "60")
    update_job_status(jobname, time, "80")
    update_job_status(jobname, time, "100")
    finish_job(jobname, time)
    
