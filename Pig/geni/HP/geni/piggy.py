#! /usr/bin/python

import Runner, re, TCSendData, PigOutputReader

percentComplete = re.compile(r"([0-9]{1,3}\%)")

def testa(output):
	match = percentComplete.search(output)
	if (match != None):
		print "A: " + match.group(0)
	
def testb(output):
	match = percentComplete.search(output)
	if (match != None):
		print "B: " + match.group(0)
	
def testc(output):
	match = percentComplete.search(output)
	if (match != None):
		print "C: " + match.group(0)

a_reader = PigOutputReader.RunningProcess("Process_1A", "HP", "Processing of an input file")
b_reader = PigOutputReader.RunningProcess("Process_1B", "Kaiserslautern", "Processing of an input file")
		
a = Runner.RunningProcess(["/home/hadoop/geni/start1a.sh"], [a_reader.process_lines])
b = Runner.RunningProcess(["/home/hadoop/geni/start1b.sh"], [b_reader.process_lines])
a.start()
b.start()
print("Waiting for step 1");
a.wait()
b.wait()

c_reader = PigOutputReader.RunningProcess("Combine", "Northwestern", "Combining the outputs of the previous processes")
c = Runner.RunningProcess(["/home/hadoop/geni/start2.sh"], [c_reader.process_lines])
c.start()
print("Waiting for step 2");
c.wait()
print("Done!");

