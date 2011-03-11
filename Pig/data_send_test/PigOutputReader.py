'''
Created on 2011-03-09

@author: cmatthew
'''
import datetime
import TCSendData


class RunningProcess():
	def __init__(self, name, site, description):
		self.jobstuff = {}
		self.jobstuff['name'] = name
		self.jobstuff['started'] = False
		self.jobstuff['site'] = site # how do we find this?
		self.jobstuff['startTime'] = datetime.datetime.now()
		self.jobstuff['startTimeStr'] = str(self.jobstuff['startTime'])
		self.jobstuff['description'] = description
		self.jobstuff['size'] = "-1" #fix me, we dont know this until after the job runs		
		self.jobstuff['finished'] = False
	
	
	def process_lines(self, line):
		line = line.strip()
		print line

		#tokens = line.split()
		#print tokens

		if line.find("%") != -1:
			tokens = line.split()
			percent = tokens[len(tokens)-2]
			pctage = percent[:len(percent)-2] # strip off the % sign
			now = datetime.datetime.now()
			elapsed = (now - self.jobstuff['startTime']).seconds
			TCSendData.update_job_status(self.jobstuff['name'], str(elapsed), pctage )

		if line.find("MR plan size after optimization:") != -1:
			tokens = line.split()
			self.jobstuff['nodes'] = tokens[len(tokens)-1]
		if line.find("totalInputFileSize") != -1:
			tokens = line.split()
			self.jobstuff['size'] = tokens[len(tokens)-1].split("=")[1]

		if (line.find("org.apache.pig.backend.hadoop.executionengine.mapReduceLayer.MapReduceLauncher") != -1) and not self.jobstuff['started']:
			self.jobstuff['started'] = True
			TCSendData.send_new_job(self.jobstuff['name'],self.jobstuff['site'],self.jobstuff['startTimeStr'],self.jobstuff['nodes'],self.jobstuff['size'], self.jobstuff['description'])

		if ((line.find("Success") != -1) and (self.jobstuff['finished'] == False)):
			self.jobstuff['finished'] = True
			now = datetime.datetime.now()
			elapsed = (now - self.jobstuff['startTime']).seconds
			TCSendData.finish_job(self.jobstuff['name'], str(elapsed) )
			
	def print_jobstuff(self):
		print self.jobstuff

if __name__ == '__main__':

	test = RunningProcess()
	f = open("pig_test_output.txt")
	for l in f.readlines():
		test.process_lines(l)
	
	print test.print_jobstuff()
	
