'''
Created on 2011-03-09

@author: cmatthew
'''
import datetime
import TCSendData
jobstuff = {}

def process_lines(line):
  line = line.strip()
  print line
  
  #tokens = line.split()
  #print tokens
  
  if line.find("%") != -1:
    tokens = line.split()
    percent = tokens[len(tokens)-2]
    now = datetime.datetime.now()
    elapsed = now - jobstuff['startTime']
    TCSendData.update_job_status(jobstuff['name'], str(elapsed), percent )
  
  if line.find("MR plan size after optimization:") != -1:
    tokens = line.split()
    jobstuff['nodes'] = tokens[len(tokens)-1]
  if line.find("totalInputFileSize") != -1:
    tokens = line.split()
    jobstuff['size'] = tokens[len(tokens)-1].split("=")[1]

  if (line.find("org.apache.pig.backend.hadoop.executionengine.mapReduceLayer.MapReduceLauncher") != -1) and not jobstuff['started']:
    jobstuff['started'] = True
    TCSendData.send_new_job(jobstuff['name'],jobstuff['site'],jobstuff['startTimeStr'],jobstuff['nodes'],jobstuff['size'], jobstuff['description'])

  if line.find("Success!") != -1:
    now = datetime.datetime.now()
    elapsed = now - jobstuff['startTime']
    TCSendData.finish_job(jobstuff['name'], str(elapsed) )
    
    
if __name__ == '__main__':
  
    jobstuff['name'] = "pig_test.pig."+str(datetime.datetime.time(datetime.datetime.now()))
    jobstuff['started'] = False
    jobstuff['site'] = "UVic" # how do we find this?
    jobstuff['startTime'] = datetime.datetime.now()
    jobstuff['startTimeStr'] = str(jobstuff['startTime'])
    jobstuff['description'] = "This is a description of a pig job."
    jobstuff['size'] = "-1" #fix me, we dont know this until after the job runs
    
    f = open("pig_test_output.txt")
    for l in f.readlines():
      process_lines(l)
      
    print jobstuff
    