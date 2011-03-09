from django.template import Context, loader
from jobs.models import Job, newJob, completeJob, ServerSummary, SummaryTable, cleanup, deleteAllJobs, reset, batchAddJobs, RandomJobList, Site, Network, Server
from django.http import HttpResponse, HttpResponseRedirect
import datetime

#
# A little utility that creates a one-button form that will let the user
# indicate that a job has been completed
#


def jobCloseWidget(jobName):
     formInput = '<form method="post" action="/jobs/developer/close">'
     formInput = formInput + '<input type="hidden" name="jobID" value="' + jobName + '"/>'
     formInput = formInput + '<input type="submit" value="Close"/></form>'
     return formInput


#
# A JobView -- a renderer for a job
#
class JobView:
    def __init__(self, job):
        self.job = job
        self.name = job.name
        self.user = job.user
        self.source = job.source
        self.server = job.server
        self.startDate = job.startDate()
        if job.completed:
            self.durationEntry = job.duration
        else:
            self.durationEntry = jobCloseWidget(self.name)

chartURL = "http://chart.apis.google.com/chart?"



def dataToURLString(integerList):
     if not integerList: return ""
     result = "%d" % integerList[0]
     for i in range(1, len(integerList)):
          result = result + (",%d" % integerList[i])
     return result

#
# Abstract class to generate a chart
#

class GoogleChart:
     def genChartURL(self):
        result = '<img src="' + chartURL
        parms = self.parameters
        lastParm = parms.pop()
        for parm in parms:
            result = result + parm + '&'
        result = result + 'chf=c,s,CCCCCC|bg,s,CCCCCC&'
        sizeString = 'width="%d" height="%d"' % (self.width, self.height)
        result = result + lastParm + '" ' + sizeString + ' alt="No image!"/>'
        return result

#
# generate a bar chart for server status
#
# http://chart.apis.google.com/chart?chxl=1:|198.55.37.254|198.55.37.9|198.55.37.36|198.55.37.12&chxp=1,0.5,1.5,2.5,3.5&chxr=0,0,4|1,0,4&chxt=y,x&chbh=60,10,20&chs=500x225&cht=bvs&chco=A2C180,3D7930&chds=0,4,0,4&chd=t:1,1,0,1|1,1,1,1&chdl=Queued+Jobs|Completed+Jobs&chtt=Server++Status%20(Jobs)
# serverList is a list of jobs.models.ServerSummary

class ServerStatusBarChart(GoogleChart):
     def __init__(self, serverList):
          addresses = "chxl=1:"
          totalQueuedJobs = []
          totalCompletedJobs = []
          maxJobs = 4
          xTicks = "chxp=1"
          nextTick = 0.5
          for server in serverList:
               addresses = addresses + "|" + server.address
               totalCompletedJobs.append(server.totalCompletedJobs)
               totalQueuedJobs.append(server.totalOpenJobs)
               if server.totalJobs > maxJobs:
                    maxJobs = server.totalJobs
               nextTickString = "%3.1f" % nextTick
               xTicks = xTicks + "," + nextTickString
               nextTick = nextTick + 1.0
          queuedData = dataToURLString(totalQueuedJobs)
          completedData = dataToURLString(totalCompletedJobs)
          dataString = 'chd=t:' + queuedData + '|' + completedData
          axisRange = "chxr=0,0,%d|1,0,%d" % (maxJobs, len(serverList))
          self.width = (70 * len(serverList)) + 220
          self.height = 225
          chartSize = "chs=%dx%d" % (self.width, self.height)
          dataSeries = "chds=0,%d,0,%d" % (maxJobs, maxJobs)
          self.parameters = [addresses, xTicks, axisRange, 'chxt=y,x',
                             'chbh=60,10,20',chartSize,'cht=bvs',
                             'chco=A2C180,3D7930', dataSeries, dataString,
                             'chdl=Queued+Jobs|Completed+Jobs',
                             'chtt=Server++Status%20(Jobs)']

class ServerStatusPane:
     def __init__(self, servers, serverViewers):
          numServers = len(servers)
          # self.cloudMap = CloudMap(serverViewers)
          self.numCharts = numServers/10
          if numServers % 10 > 0:
               self.numCharts = self.numCharts + 1
          self.barCharts = []
          nextList = []
          for server in serverViewers:
              nextList.append(server)
              if len(nextList) == 10:
                   self.barCharts.append(ServerStatusBarChart(nextList))
                   nextList = []
          if nextList:
               self.barCharts.append(ServerStatusBarChart(nextList))

     def genHTML(self):
          result = '<table border="1">'
          # result = result + "<tr>%s</tr>" % self.cloudMap.genChartURL()
          for chart in self.barCharts:
               result = result + "<tr>%s</tr>" % chart.genChartURL()
          result = result + "</table>"
          return result
          
#
# The QueueHistory for a Server
#
#http://chart.apis.google.com/chart?&chdlp=b&chls=2,4,1|1&chma=5,5,5,25

def genManhattanHistory(history):
     (xp, yp) = history[0]
     x = [xp]
     y = [yp]
     for i in range(1, len(history)):
          (nextX, nextY) = history[i]
          x.append(nextX - 1)
          y.append(xp)
          x.append(nextX)
          y.append(nextY)
          (xp, yp) = (nextX, nextY)
     return (x, y)

def generateElidedHistory(history, numPoints):
     candidates = []
     (lastX, lastY) = history[0]
     (x, y) = history[1]
     for i in range(2, len(history)):
          (nextX, nextY) = history[i]
          if (y - nextY) * (lastY - y) >= 0:
               candidates.append(i)
          (x, y) = (nextX, nextY)
     nextHistory = [history[0]]
     remainingToSkip = len(history) - numPoints
     for i in range(1, len(history)):
          if remainingToSkip == 0:
               nextHistory.append(history[i])
          elif i in candidates:
               remainingToSkip = remainingToSkip - 1
          else:
               nextHistory.append(history[i])
     if remainingToSkip > 0:
          nextHistory = nextHistory[remainingToSkip:]
     return nextHistory
     

def genHistoryForView(history):
     #
     # Manhattan histories are (probably) a bad idea....
     #
#     if len(history) < 10:
#          return genManhattanHistory(history)
     if len(history) > 150:
          history = generateElidedHistory(history, 150)
     x = []
     y = []
     for (xp, yp) in history:
          x.append(xp)
          y.append(yp)
     return (x, y)

class LocationSummary:
     def __init__(self, location, completedJobs=0, openJobs=0):
          self.completedJobs = completedJobs
          self.openJobs = openJobs
          self.location = location
          

     def addJobs(self, completedJobs, openJobs):
          self.completedJobs = self.completedJobs + completedJobs
          self.openJobs = self.openJobs + openJobs
                  
   
class QueueHistory(GoogleChart):
     def __init__(self, server, maxTime, maxJobs):
          self.parameters = ["cht=lxy",
                             "chtt=Queue+History+ for+%s" % server.address,
                             "chco=000000",
                             "chxl=0:|Time|1:|Jobs",
                             "chxt=x,y",
                             "chdl=Jobs+In+Queue",
                             "chxs=0,000000|1,000000",
                             "chs=440x220"]
          self.width=500
          self.height=250
          (x, y) = genHistoryForView(server.history)
          xString = dataToURLString(x)
          yString = dataToURLString(y)
          self.parameters.append('chd=t:'+ xString + '|' + yString)
          self.parameters.append('chxr=0,0,%d|1,0,%d' % (maxTime, maxJobs))
          self.parameters.append('chds=0,%d,0,%d' % (maxTime, maxJobs))
          xLabelPos = maxTime >> 1
          yLabelPos = maxJobs >> 1
          self.parameters.append('chxp=0,%d|1,%d' % (xLabelPos, yLabelPos))

#
# http://chart.apis.google.com/chart?cht=map&chs=600x350&chld=US-CA|US-IL|US-WA|US-FL|US-ME&chdl=Palo+Alto|Northwestern&chco=B3BCC0|333377|22BC00|B3BCC0&chtt=Jobs+At+Cloud+Sites&chm=f20,000000,0,0,40|f40,000000,0,1,40

# Summarize the jobs by locations, and put it in a GoogleMap.
# Note that the summary relies on location being a good key for
# a hash table.  Right now, this works because we're handing out one
# pointer per location in ServerViewer, but when this code gets
# decently refactored that needs to be looked at...

class CloudMap(GoogleChart):
     backgroundColor = 'FFFFFF'
     colors = ['333377', '22BC00', 'FF0000', '00FF00', '0000FF', 'DD2222',
               '22DD22', '2222DD']
     def __init__(self, serverList):
          self.locations = {}
          for server in serverList:
               location = server.location
               if location in self.locations:
                    summary = self.locations[location]
                    summary.addJobs(server.totalCompletedJobs, server.totalOpenJobs)
               else:
                    self.locations[location] = LocationSummary(location, server.totalCompletedJobs, server.totalOpenJobs)
          self.parms = {
               'chart Type' : 'cht=map',
               'chart Size' : 'chs=600x350',
               'chart Title' : 'chtt=Jobs+At+Cloud+Sites (Open/Completed)',
          } 
          self.width = 600
          self.height = 350
          colors = 'chco=' + CloudMap.backgroundColor + '|'
          siteValueSep = 'chdl='
          sites = ''
          regions = ''
          values=''
          dataValueSep='chm='
          regionValueSep='chld='
          values = ''
          currentColorIndex = 0
          dataIndex = 0
          for location in self.locations:
               summary = self.locations[location]
               colors = colors + CloudMap.colors[currentColorIndex] + '|'
               currentColorIndex = currentColorIndex + 1
               if currentColorIndex == len(CloudMap.colors):
                    currentColorIndex = 0
               sites = sites + siteValueSep + location.placeName
               regions = regions + regionValueSep + location.isoDesignation
               values = values + dataValueSep + "f%d/%d,000000,0,%d,40" % (summary.completedJobs, summary.openJobs, dataIndex)
               siteValueSep=regionValueSep=dataValueSep='|'
               dataIndex = dataIndex + 1
          regions = regions + '|US-WA|US-FL|US-ME'
          colors = colors + CloudMap.backgroundColor
          self.parms['Regions'] = regions
          self.parms['Sites'] = sites
          self.parms['Values'] = values
          self.parms['Colors'] = colors
          self.parameters = self.parms.values()
          
          
#
# generate a GoogleMeter.  This should be extended to make
# a concrete meter
#
class GoogleMeter(GoogleChart):
    def __init__(self):
        self.parms = {
            'chartSize' : "chs=300x150",
            'axes' : "chxt=y",
            'type' : "cht=gm",
            'color' : 'chco=000000|777777'
        }
        self.width=300
        self.height=150

    def genChartURL(self):
        self.parameters = self.parms.values()
        return GoogleChart.genChartURL(self)
        
#
# generate a meter for a Server, showing its current queue
#
class LoadMeter(GoogleMeter):
    def __init__(self, server, summary):
        GoogleMeter.__init__(self)
        maxQueue = summary.maxQueueSize
        if maxQueue < 10: maxQueue = 10
        meanQueue = 1.0 * summary.totalQueuedJobs/len(summary.servers)
        space = 1.0 * abs(meanQueue - server.totalOpenJobs)/maxQueue
        if space > 0.25:
             self.parms['marker'] = 'chl=Load|Mean'
        else:
             self.parms['marker'] = 'chl=Load'
        self.parms['labels'] = "chxl=0:|empty|half|full"
        self.parms['title'] = "chtt=Server+Load+for+%s" % server.address
        self.parms['range'] = "chds=0,%d" % maxQueue
        self.parms['value'] = "chd=t:%d,%d" % (server.totalOpenJobs, meanQueue)

       

#
# Compute value-min as a proportion of min-max, then complement
# (so max is normalized to 0 and min is normalized to 1)
#
def computeValueInRangeAndComplement(minVal, maxVal, val):
     totalRange = 1.0 * (maxVal - minVal)
     normalizedValue = 1.0 * (val - minVal)/totalRange
     return 1.0 - normalizedValue
     
     

class PerfMeter(GoogleMeter):
     def __init__(self, server, summaryTable):
          GoogleMeter.__init__(self)
          maxTime = summaryTable.maxServerAggregate
          minTime = summaryTable.minServerAggregate
          mean = 50
          serverPerformance = 50
          if maxTime >  minTime:
               mean =  100 * computeValueInRangeAndComplement(minTime, maxTime, summaryTable.meanJobDuration)
               if server.averageDuration > 0:
                    serverPerformance = 100 * computeValueInRangeAndComplement(minTime, maxTime, server.averageDuration())
          if abs(serverPerformance - mean) > 25:
               self.parms['marker'] = "chl=Performance|Mean"
          else:
               self.parms['marker'] = "chl=Performance"
          
          self.parms['labels'] = "chxl=0:|min|max"
          self.parms['title'] = "chtt=Server+Performance+for+%s" % server.address
          self.parms['range'] = "chds=0,100"
          self.parms['value'] = "chd=t:%d,%d" % (serverPerformance, mean)
               
          
#
# A place where a server lives
#
class Location:
     def __init__(self, placeName, isoDesignation):
          self.placeName = placeName
          self.isoDesignation = isoDesignation
          

#
# A ServerViewer
#

class ServerViewer:
#    paloAlto = Location('Palo Alto', 'US-CA')
#    northwestern = Location('Northwestern', 'US-IL')
    def __init__(self, server, summaryTable):
        self.server = server
        # knock the trailing port number off server, if it's there:
        # screws up the spacing on the charts...
        ## if server.address.startswith('http:'):
        ##      address = server.address[7:]
        ## else: address = server.address
        ## portIndex = address.find(":")
        ## if portIndex > -1:
        ##      self.address = address[:portIndex]
        ## else: self.address = address
        # self.location = self.getLocation(self.address)
        self.address = server.address.ipAddr
        self.location = server.location
        self.totalJobs = server.totalJobs
        self.totalCompletedJobs = server.totalCompletedJobs
        self.totalOpenJobs = server.totalOpenJobs
        self.averageDuration = server.averageDuration
        self.loadMeter = LoadMeter(self, summaryTable)
        self.queuedLoadURL = self.loadMeter.genChartURL()
        self.perfMeter = PerfMeter(self, summaryTable)
        self.performanceURL = self.perfMeter.genChartURL()
        self.history = server.history
        self.summaryTable = summaryTable
        self.historyURL = self.calledHistoryURL()

    def calledHistoryURL(self):
         historyQueue = QueueHistory(self.server, self.summaryTable.maxTime, self.summaryTable.maxQueueSize)
         return historyQueue.genChartURL()

    #
    # Terrible hardcoded hack that I must replace with a database reference
    # in jobs.models (needs to be a Server model with location and address)
    #

    ## def getLocation(self, unicodeAddress):
    ##      address = str(unicodeAddress)
    ##      if address == '127.0.0.1': return ServerViewer.paloAlto
    ##      elif address.startswith('198.55'): return ServerViewer.paloAlto
    ##      else: return ServerViewer.northwestern

def filterJobList(serverSite, job_list):
     if not serverSite: return job_list
     print 'Filtering for site ' + serverSite
     result = []
     for job in job_list:
          location = job.getLocation()
          print 'location of job ' + job.__unicode__() + ' is ' + location
          if location == serverSite:
               result.append(job)
     return result
     

#
# Common body between index and requestResult
#

gangliaURLs = {
     'HP' : 'http://transcloud.dyndns.org/ganglia/?r=hour&s=descending&c=tcloud-pms',
     'Northwestern' : 'http://transcloud.dyndns.org/ganglia/?r=hour&s=descending&c=nw-pms',
     'Kaiserslautern' : 'http://transcloud.dyndns.org/ganglia/?r=hour&s=descending&c=ks-pm'
     }

defaultGangliaURL = 'http://66.183.89.113:8080/ganglia/'

def getContext(serverSite = None):
    job_list = Job.objects.all()
    jobList = filterJobList(serverSite, job_list)
    latest_job_list = []
    for job in jobList:
         latest_job_list.append(JobView(job))
    # latest_job_list = makeJobList(serverSite, job_list)
    summaryTable = SummaryTable(jobList)
    serverList = summaryTable.servers
    server_list = []
    for server in serverList:
        server_list.append(ServerViewer(server, summaryTable))
    statusPane = ServerStatusPane(serverList, server_list)
    paneHTML = statusPane.genHTML()
    latest_site_list = Site.objects.all()
    latest_net_list = Network.objects.all()
    if serverSite and serverSite in gangliaURLs:
         gangliaURL = gangliaURLs[serverSite]
    else: gangliaURL = defaultGangliaURL

    gangliaFrameCode = '<iframe id="gangliaFrame" src="%s" '  % gangliaURL
    gangliaFrameCode += 'width="100%" height=1024>\n'
    gangliaFrameCode += '<p>Your browser does not support iframes.</p>\n</iframe>\n'
         
    c = Context({
        'latest_job_list': latest_job_list,
        'server_list':server_list,
        'summary_panel':paneHTML,
        'latest_site_list': latest_site_list,
        'latest_net_list':latest_net_list,
        'ganglia_url': gangliaURL,
         'ganglia_frame_code': gangliaFrameCode,
        'location' : serverSite
    })
    return c
    
#
# The front page of the Cloudboard
#

def index(request):
    c = getContext()
    t = loader.get_template('cloudboard/index.html')
    return HttpResponse(t.render(c))

def siteDetail(request, siteName):
    c = getContext(siteName)
    print 'Getting detail for site ' + siteName
    t = loader.get_template('cloudboard/index.html')
    return HttpResponse(t.render(c))

#
# The developer front page -- very similar to the front page,
# but with some added options for
# manual maintenance
#

def developer(request):
     c = getContext()
     t = loader.get_template('cloudboard/developer.html')
     return HttpResponse(t.render(c))

def convertToInt(numAsString, valueIfError, minVal, maxVal):
     try:
          result = int(numAsString)
     except ValueError:
          result = valueIfError
     if result < minVal: result = minVal
     if result > maxVal: result = maxVal
     return result


def developerCleanup(request):
     action = request.POST['action']
     try: 
          if action == 'deleteAll':
               deleteAllJobs()
          elif action == 'reset':
               reset()
          elif action == 'resetToRandom':
               numJobs = convertToInt(request.POST['numJobs'], 1000, 2, 10000)
               numServers = convertToInt(request.POST['numServers'], 10, 1, 128)
               randomJobs = RandomJobList.createRandomJobList(numJobs, numServers)
               deleteAllJobs()
               batchAddJobs(randomJobs)               
          else:
               cleanup()
          return HttpResponseRedirect('/jobs/developer/')
     except Exception, err:
          errorMessage = "Error occured on action " + action + ': ' + err.message
          return HttpResponseRedirect('/jobs/developer/errorResult?msg="' +
                                      errorMessage + '"')
              
#
# An errorResult -- this is a hack to get around the fact that we can't
# pass a Context to an HttpResponseRedirect, so we need to pass status
# in the body of a GET request.  This thing is such a request, and it
# will just display the result and the errorMessage
#

def doErrorResult(request, template):
    c = getContext()
    c['errorMessage'] = request.GET['msg']
    t = loader.get_template(template)
    return HttpResponse(t.render(c))

def errorResult(request):
     return doErrorResult(request, 'cloudboard/errorResult.html')

def developerErrorResult(request):
     return doErrorResult(request, 'cloudboard/developerErrorResult.html')



def addForm(request):
    response = "<h1>Add Jobs</h1>"
    response = response + '<table><tr><td>Single Job Input</td></tr><tr><td><form action="/jobs/developer/add/" method="post">'
    for fieldName in ['jobID', 'server', 'user', 'source', 'options', 'startTime', 'endTime']:
        response = response + fieldName + ': <input type="text" name="' + fieldName + '" '
        response = response + 'id="' + fieldName + '"><br>'
    response = response + '<input type="submit" value="Add"><br></form></td></tr>'
    response = response + '<tr><td>Batch Input.</td></tr><tr><td>  Enter the jobs to be added, as a string of '
    response = response + 'the form job1|job2|job3...'
    response = response + 'Each job is of the form name,server,user,source,options,startTime,endTime.'
    response = response + ' startTime and endTime are optional parameters.'
    response = response + '  Time is specified in the form Day Month Date Hour:Minute:Second Year.'
    response = response + ' Day is three letters, month is three letters, hour is 00-23, year is four digits.'
    response = response + '  This form is designed to be a trial of the POST method here, which I expect is what '
    response = response + ' will usually be called.</td></tr>'
    response = response + '<tr><td><form action="/jobs/developer/batchAdd/" method="post">'
    response = response + '<tr><td><table><tr><td><textarea name="batchInput" rows="20" cols="50"></textarea></td></tr>'
    response = response + '<tr><td>Batch Input</td></tr>'
    response = response + '<tr><td><input type="submit" value="Submit"/></td></tr>'
    response = response + '</table></form></td></tr></table>'
    return HttpResponse(response)

def parseDate(field):
     return datetime.datetime.strptime(field, "%a %b %d %H:%M:%S %Y")
   

def parseDateCatchError(field):
     if not field: return None
     try:
          return  parseDate(field)
     except ValueError:
          return None


def doAdd(request, redirect, errorRedirect):
    try:
        name=request.POST['jobID']
        server=request.POST['server']
        user=request.POST['user']
        source=request.POST['source']
        options=request.POST['options']
        startTimeField = request.POST['startTime']
        endTimeField = request.POST['endTime']
        startTime = parseDateCatchError(startTimeField)
        endTime = parseDateCatchError(endTimeField)
        if startTime and endTime:
             newJob(name, server, user, source, options, startTime, True, endTime)
        elif startTime:
             newJob(name, server, user, source, options, startTime)
        else: newJob(name, server, user, source, options)
        return HttpResponseRedirect(redirect)
    except Exception, e:
        errorMessage = "Error occured on adding job " + name  + ": " + e.message
        return HttpResponseRedirect(errorRedirect + '?msg="' + errorMessage + '"')

def add(request):
     return doAdd(request, '/jobs/', '/jobs/errorResult')

def developerAdd(request):
     return doAdd(request, '/jobs/developer/', '/jobs/developer/errorResult')

def parseJobDescriptor(jobDescriptor):
     fields = jobDescriptor.split(',')
     if len(fields) > 7:
          raise BadJobDescriptor(jobDescriptor)
     elif len(fields) < 5:
          raise BadJobDescriptor(jobDescriptor)
     elif len(fields) == 6:
          fields[5] = parseDate(fields[5])
          fields.append(False)
          fields.append(datetime.datetime.now())
     elif len(fields) == 7:
          fields[5] = parseDate(fields[5])
          endDate = parseDate(fields[6])
          fields[6] = True
          fields.append(endDate)
     else:
          fields.append(datetime.datetime.now())
          fields.append(False)
          fields.append(datetime.datetime.now())
     return tuple(fields)
     

def developerBatchAdd(request):
     try:
          batchInput = request.POST['batchInput'].strip()
          jobListAsString = batchInput.split('|')
          jobTuples = []
          for jobDescriptor in jobListAsString:
               jobTuple = parseJobDescriptor(jobDescriptor)
               jobTuples.append(jobTuple)
          batchAddJobs(jobTuples)
          return HttpResponseRedirect('/jobs/developer')
     except Exception, e:
          errorMessage = "Error occured on batch add:  " + e.message
          return HttpResponseRedirect('/jobs/developer/errorResult?msg="' + errorMessage + '"')

def doClose(request, redirect, errorRedirect):
    try:
        name = request.POST['jobID']
        completeJob(name)
        return HttpResponseRedirect(redirect)
    except Exception, e:
        errorMessage = "Error occured on adding job " + name  + ": " + e.message
        return HttpResponseRedirect(errorRedirect + '?msg="' + errorMessage + '"')

def close(request):
     return doClose(request, '/jobs/', '/jobs/errorResult')

def developerClose(request):
     return doClose(request, '/jobs/developer/', '/jobs/developerErrorResult')
 


def api_submit_new_hadoop_job(request):
     name = request.POST['name']
     site = request.POST['site']
     startTime = request.POST['startTime'] 
     nodes = request.POST['nodes'] 
     size = request.POST['size'] 
     description = request.POST['description']
     
     # TODO make the job

     return HttpResponse("Created: %s, %s"%(name,site))

def api_update_hadoop_job(request):
     
     name = request.POST['name']
     percent = request.POST['percent']
     timeInSec = request.POST['timeInSec']
     
     # TODO update job here

     return HttpResponse("%s updated to, %s"%(name,percent))

def api_finish_hadoop_job(request):

     name = request.POST['name']
     timeInSec = request.POST['timeInSec']

     #TODO call finish here

     return HttpResponse("Finished %s"%(request.POST['name']))
