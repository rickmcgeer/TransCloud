from django.db import models
import datetime
import random

#
# A utility to clean up the database, needed because we can screw it
# up in testing....
#

def cleanup():
    jobs = Job.objects.all()
    unique = {}
    for job in jobs:
        if job.name in unique:
            job.delete()
        else:
            unique[job.name] = job

#
# And a utility to blow away all the jobs
#

def deleteAllJobs():
    Job.objects.all().delete()
        
            
    
#
# A Job.   Fields as follows:
# startTime: datetime.datetime: time the job started
# endTime:  datetime.datetime: time the job ended
# duration: integer: endTime - startTime, in seconds
# server: IPv4 address: where the job is queued up/was done.
# completed: Boolean: whether the job is done.  endTime and duration are only
#                     meaningful when this is True
# name: string (max 200): the ID of the job.  NOTE THIS MUST BE UNIQUE!
# user: string (max 200): name of the user this was done for.  Typically an
#                      email address
# source: URL: URL of the source stream
# options: string (max 200): options on the job
#

class Job(models.Model):
    startTime = models.DateTimeField('Start Time')
    endTime = models.DateTimeField('End Time')
    duration = models.IntegerField('Duration')
    server = models.IPAddressField('Server')
    completed = models.BooleanField('Done')
    name = models.CharField('job id', max_length = 200)
    user = models.CharField('user email', max_length = 200)
    source = models.URLField('Source URL')
    options = models.CharField('Job Options', max_length = 200)

    #
    # Meaningful string for the job
    #

    def __unicode__(self):  
        result = 'Job %s, user %s, source %s, server %s, started %s' % (self.name, self.user, self.source, self.server, self.startTime.__str__())
        # result = 'Job ' + self.name
        if self.completed:
            return result + ', duration %d seconds' % self.duration
        else:
            return result + ' still in progress'

    def startDate(self):
        return self.startTime.strftime("%A, %d. %B %Y %I:%M%p")

    def totalTime(self):
        if self.completed: return '%d' % self.duration
        else: return 'N/A'

    def getLocation(self):
        ipAddr = IPAddr(self.server)
        serverRecord = Server.objects.get(ipAddr=ipAddr.ipAddr)
        return serverRecord.location
        
        
        

#
# a convenience function to create a newJob.  Takes in the name, server,
# user, source, and options fields.  Default values are filled in for
# startTime (now), endTime (now), and completed (False) if not present,
# and duration is computed if completed = True
#

def newJob(name, server, user, source, options,
           startTime = datetime.datetime.now(), completed=False,
           endTime=datetime.datetime.now()):
    if not Job.objects.filter(name=name):
        if completed:
            duration = durationInSeconds(startTime, endTime)
        else: duration = -1
        job = Job(name=name, server=server, user=user, source=source,
                  options=options, startTime=startTime,
                  completed=completed, endTime = endTime,
                  duration = duration)
        job.save()
        return job.id
    else:
        raise DuplicateJobError(name)

#
# a convenience function to batch add a bunch of jobs as a list
# The jobs are in tuples (name, server, user, source, options, startTime,
# completed, endTime).  If completed, endTime is meaningful, otherwise
# not
#

def batchAddJobs(jobList):
    for  (name, server, user, source, options, startTime, completed, endTime) in jobList:
        if completed:
            newJob(name, server, user, source, options, startTime, completed, endTime)
        else:
            newJob(name, server, user, source, options, startTime)
            

#
# A utility to reset to the initial database, for testing
#
def reset():
    deleteAllJobs()
    newJob('job1', '198.55.37.9', 'rick@mcgeer.com','http://www.foo.com/bar.flv','-s 324x240')
    newJob('job2','198.55.37.9', 'rick@mcgeer.com','http://www.baz.com/bar1.flv','-s 324x240')
    newJob('job3','198.55.37.12','marcoy@gmail.com','http://www.bar.com/foo.mp4','-s 324x240')
    newJob('job5','198.55.37.12','acb@cs.princeton.edu','http://www.yahoo.com/banner.mp2','-s 324x240')
    newJob('job6','198.55.37.254','alvin@cal.berkeley.edu','http://www.calbears.com/the_play.flv','-s 324x240')
    newJob('job7','198.55.37.254','celliott@bbn.com','http://www.baz.com/foo.flv','-s 324x240')
    newJob('job10','198.55.37.36','j-mambretti@northwestern.edu','http://www.glif.is/map.mp4','-s 324x240')


#
# Attempted to add  a duplicate job
#
class DuplicateJobError(Exception):
    def __init__(self, jobId):
        self.jobId = jobId
        self.message = "Attempted to add a second job with ID " + jobId

    def __str__(self):
        return self.message

#
# Attempted to add  a duplicate job
#
class CloseCompletedJobError(Exception):
    def __init__(self, jobId):
        self.jobId = jobId
        self.message = "Attempted to complete completed job " + jobId

    def __str__(self):
        return self.message
#
# A little utility to compute a time delta in seconds.  I've tested endTime > startTime
# Note there are 24*60*60 = 86400 seconds in a day
#
def durationInSeconds(startTime, endTime):
    durationAsTimeDelta = endTime - startTime
    return durationAsTimeDelta.days * 86400 + durationAsTimeDelta.seconds
    

#
# Note that a job with name name is done.  Sets completed, notes endTime,
# computes duration.
# 

def completeJob(name):
    job = Job.objects.get(name=name)
    if not job.completed:
        job.completed = True
        job.endTime = datetime.datetime.now()
        job.duration = durationInSeconds(job.startTime, job.endTime)
        job.save()
    else:
        raise CloseCompletedJobError(name)

# the beginning of time, as far as we're concerned...no job can have a start or end time
# before this.  hack to avoid figuring out what the min event is, which we can do if
# this becomes a problem

beginningOfTime = datetime.datetime(2010, 10, 1)

def computeBeginningOfTime(servers):
    serverList = []
    for server in servers:
        if server.hasJobs(): serverList.append(server)
    if not serverList: return beginningOfTime
    earliestTime = serverList.pop().earliestTime()
    for server in serverList:
        time = server.earliestTime()
        if time < earliestTime:
            earliestTime = time
    return earliestTime

#
# A dumb little utility
#
def last(myList):
    return myList[len(myList) - 1]

#
# A little utility to take apart a string representing a well-formed URL (no
# error-checking done) and pull out the various parts.  Assumes no DNS; the
# address chunk is a valid IPv4 address, with an optional port
# input: the string to be taken apart
# fields:
#   protocol (optional): http, smtp, ftp, etc...
#   ipAddr: the valid IPv4 address
#   port (optional): a port annotation to the address
#   path (optional): anything after the port (has to be demarcated with a /)
#
# some valid calls:
#  IPAddr("http://198.62.256.32:8080/foo/bar/baz.html")
#  IPAddr("198.62.256.32")
#  IPAddr("198.62.256.32/foo/bar/baz.html")
#  IPAddr("http://198.62.256.32:8080")
#  IPAddr("198.62.256.32:8080")
# ..etc...
#
# __unicode__(self) rebuilds the string from the components for debugging:
# so
# foo = IPAddr(s)
# foo
# should print s
#
# Uses split() repeatedly instead of re for reliability and readability....
#

class IPAddr:
     def __init__(self, ipAddrString):
         firstCut = ipAddrString.split("://")
         if len(firstCut) == 2:
             self.protocol = firstCut[0]
             rest = firstCut[1]
         else:
             self.protocol = None
             rest = firstCut[0]
         nextCut = rest.split("/")
         rawIPAddr = nextCut[0]
         if len(nextCut) > 1: self.path = '/'.join(nextCut[1:])
         else: self.path = None
         lastCut = rawIPAddr.split(':')
         self.ipAddr = lastCut[0]
         if len(lastCut) == 2: self.port = lastCut[1]
         else: self.port = None
         self.inputString = ipAddrString

     def __unicode__(self):
         if self.protocol: result = self.protocol + "://" + self.ipAddr
         else: result = self.ipAddr
         if self.port: result = result + ":" + self.port
         if self.path: result = result + "/" + self.path
         return result

     def __str__(self):
         return self.__unicode__()

#
# A class for per-server statistics. 
#

class ServerSummary:
    def __init__(self, ipAddr):
        self.address = IPAddr(ipAddr)
        self.totalJobs = 0
        self.totalCompletedJobs = 0
        self.totalCompletedDuration = 0
        self.totalOpenJobs = 0
        self.openJobs = []
        self.completedJobs = []
        self.queueHistory = {}
        self.serverRecord = Server.objects.get(ipAddr=self.address.ipAddr)
        if self.serverRecord:
            self.location = self.serverRecord.location
        else:
            raise ServerNotFoundObjection(ipAddr)
        
        
        
        

    def averageDuration(self):
        if self.totalCompletedJobs > 0:
            return self.totalCompletedDuration/self.totalCompletedJobs
        else: return 0

    def hasJobs(self):
        return self.openJobs or self.completedJobs

    def earliestTime(self):
        time = None
        for jobList in [self.openJobs, self.completedJobs]:
            for job in jobList:
                if time:
                    if time > job.startTime:
                        time = job.startTime
                else: time = job.startTime
        return time

    def maxQueueSize(self):
        if not self.history: return 0
        maxQSize = 0
        for (time, qSize) in self.history:
            if qSize > maxQSize: maxQSize = qSize
        return maxQSize
        

    #
    # Compute the queue history since beginningOfTime for this server: the
    # number of jobs in the queue at each second since the beginning of time
    # This is represented as a  list of pairs (t_i, n_i), where t_i < t_{i+1} and
    # the number in the queue is n_i in the interval
    # [t_i, t_{i+1}).  This is in the variable self.history
    #

    def computeQueueHistory(self, beginningOfTime):
        startEvents = []
        endEvents = []
        for job in self.openJobs:
            startTimeInSeconds = durationInSeconds(beginningOfTime, job.startTime)
            startEvents.append(startTimeInSeconds)
        for job in self.completedJobs:

            startTimeInSeconds = durationInSeconds(beginningOfTime, job.startTime)
            startEvents.append(startTimeInSeconds)
            endTimeInSeconds = durationInSeconds(beginningOfTime, job.endTime)
            endEvents.append(endTimeInSeconds)
        startEvents = sorted(startEvents)
        endEvents = sorted(endEvents)
        startEvents.reverse()
        endEvents.reverse()
        #
        # now just build the queue history
        #
        self.history = [(0,0)]
        current = 0
        while (startEvents and endEvents):
            lastStart = last(startEvents)
            lastEnd = last(endEvents)
            if lastStart < lastEnd:
                nextTime = startEvents.pop()
                current = current + 1
                self.history.append((nextTime, current))
            elif lastStart > lastEnd:
                nextTime = endEvents.pop()
                current = current - 1
                self.history.append((nextTime, current))
            # else do nothing -- we could add both, and I'll leave that for later decision
            # but this is why this code is verbose, so we can handle this case easily in
            # future
            else:
                startEvents.pop()
                endEvents.pop()
        while startEvents:
            nextTime = startEvents.pop()
            current = current + 1
            self.history.append((nextTime, current))
        while endEvents:
            nextTime = endEvents.pop()
            current = current - 1
            self.history.append((nextTime, current))

    def addLastValue(self, maxTimeInSeconds):
        (time, value) = self.history[len(self.history) - 1]
        self.history.append((maxTimeInSeconds, value))

    def maxTime(self):
        (time, value) = self.history[len(self.history) - 1]
        return time
            
    def __str__(self):
        result = self.address + " totalJobs: %d, totalCompleted: %d, totalOpen: %d" % (self.totalJobs, self.totalCompletedJobs, self.totalOpenJobs)
        if self.totalCompletedJobs > 0:
            result = result + ", Average Duration: %d" % self.averageDuration()
        result = result + ", Open jobs: "+ self.openJobs.__str__()
        result = result + ", Completed jobs: " + self.completedJobs.__str__()
        return result
    
class ServerNotFoundException(Exception):
    def __init__(self, ipAddr):
        self.ipAddr = ipAddr
        self.message = "No such server found in the database: " + ipAddr

    def __str__(self):
        return self.message

#
# Compute and return a summary table for servers.  This will return
# a  list of ServerSummaries, one per server.
# Code is dirt simple: iterate over jobs, computing summary statistics
# for each server in the most obvious way possible
#

class SummaryTable:
    def __init__(self, jobs):
        if not jobs:
            self.servers = []
            return
        servers = {}
        self.totalQueuedJobs = 0
        for job in jobs:
            if  servers.has_key(job.server):
                summary = servers[job.server]
            else:
                summary = ServerSummary(job.server)
                servers[job.server] = summary
            summary.totalJobs = summary.totalJobs + 1
            if job.completed:
                summary.totalCompletedJobs = summary.totalCompletedJobs + 1
                summary.totalCompletedDuration += job.duration
                summary.completedJobs.append(job)
            else:
                summary.totalOpenJobs = summary.totalOpenJobs + 1
                self.totalQueuedJobs = self.totalQueuedJobs + 1
                summary.openJobs.append(job)
        self.servers = servers.values()
        self.computeQueueHistory()
        self.serverPerformanceAggregate()

    def serverPerformanceAggregate(self):
        totalJobs = 0
        maxTime = 0
        minTime = -1
        totalDuration = 0
        for server in self.servers:
            totalJobs = totalJobs + server.totalCompletedJobs
            totalDuration = totalDuration + server.totalCompletedDuration
            duration = server.averageDuration()
            if duration == 0: continue
            if duration > maxTime:  maxTime = duration
            if (minTime == -1) or (duration < minTime):
                minTime = duration
        self.minServerAggregate = minTime
        self.maxServerAggregate = maxTime
        if totalJobs > 0:
            self.meanJobDuration = totalDuration/totalJobs
        else:
            self.meanJobDuration = 0

    def computeQueueHistory(self):
        beginningOfTime = computeBeginningOfTime(self.servers)
        delta = datetime.timedelta(seconds = 10)
        beginningOfTime = beginningOfTime - delta
        for server in self.servers:
            server.computeQueueHistory(beginningOfTime)
        self.maxTime = 0
        for server in self.servers:
            time = server.maxTime()
            if time > self.maxTime: self.maxTime = time
        self.maxTime = self.maxTime + 10
        for server in self.servers:
            server.addLastValue(self.maxTime)
        self.maxQueueSize = 0
        for server in self.servers:
            serverMaxQueue = server.maxQueueSize()
            if serverMaxQueue > self.maxQueueSize:
                self.maxQueueSize = serverMaxQueue
        

    def __str__(self):
        result = "["
        for server in self.servers:
            result = result + server.__str__() + ", "
        result = result + "]"
        return result

class RandomJobList:
     urls=["foo.com", "bar.com", "baz.com", "ucsd.edu", "hp.com",
      "northwestern.edu", "geni.net", "princeton.edu", "uvic.ca",
      "uic.edu"]

     videos = ["foo.mp4", "bar.mp2", "baz.flv", "theplay.avi", "map_anim.flv",
          "foo.mp2", "bar.mp4", "baz.mp4", "theplay.mp4", "map2.flv"]
     
     @staticmethod
     def generateRandomURL():
          return 'http://www.%s/%s' % (random.choice(RandomJobList.urls), random.choice(RandomJobList.videos))
      
     users = ["rick.mcgeer@hp.com", "alvina@cs.ucsd.edu", "marcoy@uvic.ca",
         "llp@cs.princeton.edu", "celliot@bbn.com"]

     domains = ["198.55.37", "198.55.32", "16.25.12", "17.32.8", "198.55.32", "131.246.112", "165.124.3"]

     @staticmethod     
     def genRandomServer():
          domain = random.choice(RandomJobList.domains)
          node = random.randint(1, 32)
          return "%s.%d" % (domain, node)

     @staticmethod
     def genRandomStartDate():
          now = datetime.datetime.now()
          delta = random.randint(1000,86400)
          timeDelta = datetime.timedelta(0, delta)
          return now - timeDelta
      
     @staticmethod
     def genRandomEndDate(startDate):
          delta = random.randint(1000,86400)
          timeDelta = datetime.timedelta(0, delta)
          return startDate + timeDelta
      
     @staticmethod
     def genRandomOffset():
          now = datetime.datetime.now()
          delta = random.randint(0, 1000)
          timeDelta = datetime.timedelta(0, delta)
          return now - timeDelta

     @staticmethod
     def createRandomJobList(numJobs = 1000, numServers=10):
          result = []
          jobPrefix = "job_%d" % random.randint(0, 1000)
          if numServers < 1: numServers = 1
          servers = []
          for i in range(0, numServers):
              server = RandomJobList.genRandomServer()
              servers.append(server)              
          for i in range(0, numJobs):
               completed = random.randint(0, 100) < 90
               if completed:
                    startDate = RandomJobList.genRandomStartDate()
                    endDate = RandomJobList.genRandomEndDate(startDate)
               else:
                    startDate = RandomJobList.genRandomOffset()
                    endDate = datetime.datetime.now()
               name = "%s_%d" % (jobPrefix, i)
               server = random.choice(servers)
               user = random.choice(RandomJobList.users)
               options = "-s 1280x724"
               source = RandomJobList.generateRandomURL()
               result.append((name, server, user, source, options, startDate,
                              completed, endDate))
          return result

    


#
# A Site.   Fields as follows:
# name: name of the site
# lat: site latitude
# lon: site longitude
# All fields are character fields
#
class Site(models.Model):
    name = models.CharField(max_length=200)
    lat = models.CharField(max_length=200)
    lon = models.CharField(max_length=200)
    
    def __unicode__(self):
        return self.name + "@<" + self.lat + "," + self.lon + ">"

# A Network: A link between two sites
# snet: the start of the network, the name of a site
# enet: the name of the other terminus of the site
# weight: some measure of size of link -- typically an integer 0-999

class Network(models.Model):
    snet = models.ForeignKey(Site, related_name='startSite')
    enet = models.ForeignKey(Site, related_name='endSite')
    weight = models.CharField(max_length=3);

    def __unicode__(self):
        return self.snet.name + "->" + self.enet.name + ": " + self.weight


def makeSite(name, lat, lon):
    site = Site(name=name, lat=lat, lon=lon)
    site.save()

def makeLink(start, end, weight):
    site1 = Site.objects.get(name=start)
    site2 = Site.objects.get(name=end)
    net = Network(snet = site1, enet = site2, weight=weight)
    net.save()

def buildTransCloud():
    makeSite(name="UVic", lat="48.460911",lon="-123.311711")
    makeSite(name="UCSD", lat="32.877491", lon="-117.235276")
    makeSite(name="HP",lat="37.41274366798126",lon="-122.15129613876343")
    makeSite(name="Kaiserslautern", lat="49.439556958940855", lon="7.83050537109375")
    makeSite(name="Northwestern", lat= "41.89480235167352", lon="-87.6160740852356")
    makeSite(name="Amsterdam", lat="52.368649", lon="4.890201")
    makeLink("UCSD", "HP", 5)
    makeLink("HP", "Northwestern", 5)
    makeLink("Northwestern", "Amsterdam", 5)
    makeLink("Amsterdam", "Kaiserslautern", 5)

def restartSiteDB():
    Network.objects.all().delete()
    Site.objects.all().delete()
    buildTransCloud()

#
# A server.  Very simple:
# An IPv4 address (no ports), delimited in the usual way: three-digit fields separated by period,
# for a total length of 15
# A location, which must be the name of a site...
#

class Server(models.Model):
    ipAddr = models.CharField('ip address', max_length = 15)
    location = models.CharField('location', max_length = 200)

#
# a convenience function to create a newServer.  Takes in the ipAddr and location
# fields.
#

def newServer(ipAddr, location):
    if not Server.objects.filter(ipAddr=ipAddr):
        if Site.objects.filter(name=location):
            server = Server(ipAddr=ipAddr, location=location)
            server.save()
            return server.ipAddr
        else: raise NoSuchLocationError(location)
    else:
        raise DuplicateError(ipAddr)

#
# Attempted to add  a duplicate server
#
class DuplicateServerError(Exception):
    def __init__(self, ipAddr):
        self.ipAddr = ipAddr
        self.message = "Attempted to add a second server with address " + ipAddr

    def __str__(self):
        return self.message

#
# Attempted to add  a  server in a bad location
#
class NoSuchLocationError(Exception):
    def __init__(self, location):
        self.location = location
        self.message = "Attempted to add a  server at nonexistent location: " + location

    def __str__(self):
        return self.message

#
# populate with a bunch of servers
#

def addInitialServers():
    for i in [32, 37]:
        for j in range(0, 256):
            ipAddr = "198.55.%d.%d" % (i, j)
            newServer(ipAddr, "HP")
    for j in range(0, 256):
        ipAddr = "131.246.112.%d" % j
        newServer(ipAddr, "Kaiserslautern")
        ipAddr = "165.124.3.%d" % j
        newServer(ipAddr, "Northwestern")
        ipAddr = "16.25.12.%d" % j
        newServer(ipAddr, "UCSD")
        ipAddr = "17.32.8.%d" % j
        newServer(ipAddr, "Amsterdam")

def newTransCloudDB():
    Server.objects.all().delete()
    restartSiteDB()
    addInitialServers()
    jobList = RandomJobList.createRandomJobList(1000, 30)
    deleteAllJobs()
    batchAddJobs(jobList)
    
        
    
    
    
    
    


