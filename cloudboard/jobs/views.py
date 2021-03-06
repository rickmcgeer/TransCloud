from django.template import Context, loader
from jobs.models import Job, newJob, completeJob, ServerSummary, SummaryTable, cleanup, deleteAllJobs, reset, batchAddJobs, RandomJobList, Site, Network, Server, HadoopJob, newHadoopJob, topNProtocols, batchAddResults, addAnalysisResult, resultsFiled, cleanOutDatabase
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
        result = result + 'chf=c,s,CCCCCC|bg,s,FFFFFF&'
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
     # print 'Filtering for site ' + serverSite
     result = []
     for job in job_list:
          location = job.getLocation()
          # print 'location of job ' + job.__unicode__() + ' is ' + location
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

defaultGangliaURL = 'http://ganglia.trans-cloud.net/ganglia/'

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
    switched = switch_status();
    if serverSite and serverSite in gangliaURLs:
         gangliaURL = gangliaURLs[serverSite]
    else: gangliaURL = defaultGangliaURL

    gangliaFrameCode = '<iframe id="gangliaFrame" src="%s" '  % gangliaURL
    gangliaFrameCode += 'width="100%" height=1024>\n'
    gangliaFrameCode += '<p>Your browser does not support iframes.</p>\n</iframe>\n'
    
    siteViewers = []
    for site in latest_site_list:
        siteViewers.append(HadoopSiteViewer(site))
         
    c = Context({
        'latest_job_list': latest_job_list,
        'server_list':server_list,
        'summary_panel':paneHTML,
        'latest_site_list': latest_site_list,
        'latest_net_list':latest_net_list,
        'ganglia_url': gangliaURL,
        'ganglia_frame_code': gangliaFrameCode,
        'location' : serverSite,
        'site_list' : siteViewers,
        'switched' : switched
    })
    return c
    
#
# The front page of the Cloudboard
#

def index(request):
    c = getContext()
    t = loader.get_template('cloudboard/index.html')
    return HttpResponse(t.render(c))

def summaryStats(request):
    c = getContext()
    t = loader.get_template('cloudboard/summaryStats.html')
    return HttpResponse(t.render(c))

def siteDetail(request, siteName):
    c = getContext(siteName)
    t = loader.get_template('cloudboard/summaryStats.html')
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

def parseDate(field, format="%a %b %d %H:%M:%S %Y"):
     return datetime.datetime.strptime(field, format)
   

def parseDateCatchError(field, format="%a %b %d %H:%M:%S %Y"):
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
        errorMessage = "Error occured on adding job " + name  + ": " + str(e)
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
          errorMessage = "Error occured on batch add:  " + str(e)
          return HttpResponseRedirect('/jobs/developer/errorResult?msg="' + errorMessage + '"')

def doClose(request, redirect, errorRedirect):
    try:
        name = request.POST['jobID']
        completeJob(name)
        return HttpResponseRedirect(redirect)
    except Exception, e:
        errorMessage = "Error occured on adding job " + name  + ": " + str(e)
        return HttpResponseRedirect(errorRedirect + '?msg="' + errorMessage + '"')

def close(request):
     return doClose(request, '/jobs/', '/jobs/errorResult')

def developerClose(request):
     return doClose(request, '/jobs/developer/', '/jobs/developerErrorResult')

def api_clear_hadoop_jobs(request):
     HadoopJob.objects.all().delete()
     return HttpResponse('All existing Hadoop Jobs blown away')

def enterHadoopForm(request):
    c = getContext()
    t = loader.get_template('cloudboard/hadoopForm.html')
    return HttpResponse(t.render(c))
 


def api_submit_new_hadoop_job(request):
     try:
       name = request.POST['name']
       site = request.POST['site']
       startTimeField = request.POST['startTime']
       startTime = parseDateCatchError(startTimeField, "%Y-%m-%d %H:%M:%S.%f")
       if not startTime: startTime = datetime.datetime.now()
       nodestr = request.POST['nodes'] 
       sizestr = request.POST['size'] 
       description = request.POST['description']
       nodes = int(nodestr)
       size = int(sizestr)
       newHadoopJob(name, site, startTime, nodes, size, description)
       return HttpResponse("Created: %s, %s" % (name, site))
     except Exception, e:
       errorMessage = "Error occured on submitting job " + name  + ": " + str(e)
       print errorMessage
       return HttpResponseRedirect('/jobs/errorResult?msg="' + errorMessage + '"')
  

     # TODO make the job
     
  

def api_update_hadoop_job(request):
     try:
        name = request.POST['name']
        percentstr = request.POST['percent']
        timeInSecStr = request.POST['timeInSec']
        job = HadoopJob.objects.get(name=name)
        percentage=int(percentstr)
        timeInSecs=int(timeInSecStr)
        job.newTimeStamp(timeInSecs, percentage)
     except Exception, e:
        errorMessage = "Error occured on updating job " + name  + ": " + str(e)
        print errorMessage
        return HttpResponseRedirect('/jobs/errorResult?msg="' + errorMessage + '"')
     
     # TODO update job here

     return HttpResponse("%s updated to %s%s at %d seconds" % (name, percentage, "%", timeInSecs))

def api_finish_hadoop_job(request):

     try:
        name = request.POST['name']
        timeInSec = request.POST['timeInSec']
        job = HadoopJob.objects.get(name=name)
        durationInSeconds = int(timeInSec)
        job.jobEndedAfterDuration(durationInSeconds)
        return HttpResponse("Finished %s" % (request.POST['name']))
     except Exception, e:
        errorMessage = "Error occured on finishing Hadoop job " + name  + ": " + str(e)
        print errorMessage
        return HttpResponseRedirect('/jobs/errorResult?msg="' + errorMessage + '"')

     #TODO call finish here


def listToURLString(pyList):
     result = str(pyList[0])
     for i in range(1, len(pyList)):
          result = result + ',' + str(pyList[i])
     return result

def normalizeListOfNumbers(numList, multiplyFactor):
     for i in range(0, len(numList)):
          numList[i] = numList[i] * multiplyFactor

class XYDataSeries:
    def __init__(self, xData, yData, color="000000", name="Series"):
         self.xData = xData
         self.yData = yData
         self.color = color
         self.name = name

    def getDataArgument(self):
         return listToURLString(self.xData) + "|" + listToURLString(self.yData)



colors = ["FF0000", "00FF00", "0000FF", "FFFF00", "00FFFF", "FF00FF", "330000", "003300", "000033",
          "333300", "330033", "003333", "770000", "007700", "000077", "770077", "777700", "007777", "0F0000",
          "000F00", "00000F", "0F0F00", "0F000F", "000F0F", "000000", "FFFFFF"]

class OpenJobsChart(GoogleChart):
    def __init__(self, siteViewer):
         self.parameters = ["cht=lxy",
                            "chtt=Status+of+Open+Jobs+at+site " + siteViewer.siteName,
                            "chxl=0:|Time|1:|Pct",
                            "chxt=x,y,r",
                            "chxs=0,000000|1,000000",
                            "chs=440x220"]
         self.width=500
         self.height=250
         self.dataSeries = []
         maxTime = 0
         for i in range(0, len(siteViewer.currentJobs)):
              job = siteViewer.currentJobs[i]
              timeStamps = job.getTimeStamps()
              self.dataSeries.append(XYDataSeries(timeStamps, job.getPercentages(), colors[i], job.name))
              lastTime = timeStamps[len(timeStamps) - 1]
              if lastTime > maxTime: maxTime = lastTime
         absMaxTime = maxTime
              
         if maxTime > 100:
              multiplyFactor = 100.0/maxTime
              for xySeries in self.dataSeries:
                   normalizeListOfNumbers(xySeries.xData, multiplyFactor)
              maxTime = 100

         dataSeriesList = []
         colorList = []
         nameList = []

         for xySeries in self.dataSeries:
              dataSeriesList.append(xySeries.getDataArgument())
              colorList.append(xySeries.color)
              nameList.append(xySeries.name)


         dataParam = '|'.join(dataSeriesList)
         colorParam = ','.join(colorList)
         nameParam = '|'.join(nameList)
                                
         self.parameters.append('chd=t:'+ dataParam)
         self.parameters.append('chdl=' + nameParam)
         self.parameters.append('chco=' + colorParam)
         self.parameters.append('chxr=0,0,%d|1,0,100' % maxTime)
         self.parameters.append("chxl=0:|Time (Max = %d)|1:|Pct" % absMaxTime)
         # self.parameters.append('chds=0,%d,0,100' % maxTime)
         xLabelPos = maxTime >> 1
         yLabelPos = 50
         self.parameters.append('chxp=0,%d|1,%d' % (xLabelPos, yLabelPos))

def normalize(intList):
     maxList = 100
     for num in intList: maxList = max(maxList, num)
     if maxList == 100: return
     multiplier = 100.0/maxList
     for i in range(0, len(intList)): intList[i] = intList[i] * multiplier
     return

class FinishedJobsBarChart(GoogleChart):
     def __init__(self, viewer):
          self.parameters = ['chxt=y',
                             'chbh=a',
                             'chs=440x220',
                             'cht=bvs',
                             'chco=A2C180,3D7930,FF00FF',
                             'chdl=Nodes|Size|Time',
                             'chtt=Statistics+For+Closed+Jobs+At+Site+' + viewer.siteName,
                             ]
          self.width=500
          self.height=250
          nodes = []
          time = []
          size = []
          history = viewer.jobHistory
          if len(history) > 20:
               history = history[len(history) - 20:]
               
          for job in history:
               nodes.append(job.nodes)
               time.append(job.duration)
               size.append(job.size)
          normalize(nodes)
          normalize(size)
          normalize(time)
          self.parameters.append('chd=t:'+ dataToURLString(nodes) + '|' + dataToURLString(size) + '|' + dataToURLString(time))
          
               

class HadoopSiteViewer:
    def __init__(self, site):
        self.siteName = site.name
        self.currentJobs = []
        self.jobHistory = []
        hadoopJobs = HadoopJob.objects.filter(site=self.siteName)
        for hadoopJob in hadoopJobs:
            if hadoopJob.completed:
                self.jobHistory.append(hadoopJob)
            else:
                self.currentJobs.append(hadoopJob)
        if len(self.currentJobs) == 0:
             if len(self.jobHistory) > 0:
                  self.currentJobs.append(self.jobHistory[len(self.jobHistory) - 1])

    def currentJobsChart(self):
        if len(self.currentJobs) == 0:
            return "<p>No Open Jobs</p>"
        self.pctComplete = OpenJobsChart(self)
        return self.pctComplete.genChartURL()
        

    def hadoopHistory(self):
        if len(self.jobHistory) == 0:
            return "<p>No Completed Jobs</p>"
        self.finishedJobs = FinishedJobsBarChart(self)
        return self.finishedJobs.genChartURL()

    def lastJobResults(self): 
        if len(self.jobHistory) == 0: return ""
        lastJob = self.jobHistory[len(self.jobHistory) - 1]
        viewer = HadoopJobViewer(lastJob)
        return viewer.resultChartURL


          

class HadoopResultsPieChart(GoogleChart):
     def __init__(self, hadoopJobViewer):
          self.parameters = ["cht=p",
                             "chtt=Packet+Mix+By+Protocol+Job+%s" % hadoopJobViewer.name,
                             "chs=440x220"]
          (protocols, percentages) = hadoopJobViewer.topJobs
          dataString = ""
          for percentage in percentages:
               dataString = dataString  + ("%5.2f" % percentage).strip() + ","
          dataString = dataString[:len(dataString)-2]
          labelString = ('|'.join(protocols)).strip()
          myColors = colors[:len(protocols) + 1]
          colorString = (','.join(myColors)).strip()
          self.parameters.append('chd=t:' + dataString)
          self.parameters.append('chdl=' + labelString)
          self.parameters.append('chco=' + colorString)
          self.width = 440
          self.height = 220
          
          
     

class HadoopJobViewer:
     def __init__(self, hadoopJob):
          self.siteName = hadoopJob.site
          self.nodes = hadoopJob.nodes
          self.size = hadoopJob.size
          self.duration = hadoopJob.duration
          self.topJobs = topNProtocols(hadoopJob.name, 20, 0.5, True)
          self.name = hadoopJob.name
          if resultsFiled(self.name):
               self.resultsChart = HadoopResultsPieChart(self)
          else: self.resultsChart = None
          self.resultChartURL = self.genResultChartURL()
               

     def genResultChartURL(self):
          if self.resultsChart:
               return self.resultsChart.genChartURL()
          else:
               return "<p>Results not filed!</p>"
          

def includeHadoopJobInList(hadoopJob, site):
     if not hadoopJob.completed: return False
     if not site: return True
     return hadoopJob.site == site

def getHadoopContext(site = None, entryJobList = None):
     if entryJobList: jobList = entryJobList
     else:
          jobList = []
          for job in HadoopJob.objects.all():
               if includeHadoopJobInList(job, site):
                    jobList.append(HadoopJobViewer(job))
     c = Context({'hadoop_job_list': jobList})
     return c
          

def doHadoopJobTable(request, site=None):
    c = getHadoopContext(site=site)
    t = loader.get_template('cloudboard/hadoopTemplate.html')
    return HttpResponse(t.render(c))

def hadoopJobTable(request):
     return doHadoopJobTable(request, None)

def hadoopSiteTable(request, siteName):
     return doHadoopJobTable(request, siteName)

def enterHadoopResultForm(request):
     t = loader.get_template('cloudboard/hadoopResultForm.html')
     return HttpResponse(t.render(Context({'message' : None})))

def api_submit_new_hadoop_result(request):
     jobName = request.POST["name"]
     protocol = request.POST["protocol"]
     percentageAsText = request.POST["percentage"]
     percentageAsText = percentageAsText.strip("%")
     percentage = float(percentageAsText)
     addAnalysisResult(jobName, protocol, percentage)
     t = loader.get_template('cloudboard/hadoopResultForm.html')
     msg = '<p>Result %s:%s added for job %s</p>' % (jobName, protocol, percentage)
     return HttpResponse(t.render(Context({'message' : msg})))

def api_batch_hadoop_result(request):
     jobName = request.POST['name']
     entryListAsStr = request.POST['entries']
     entries = entryListAsStr.split(',')
     batchAddResults(jobName, entries)
     jobs = HadoopJob.objects.filter(name=jobName)
     c = getHadoopContext(entryJobList = jobs)
     t = loader.get_template('cloudboard/hadoopTemplate.html')
     return HttpResponse(t.render(c))

def api_clean_db(request):
     name = open("/tmp/switch.txt",'w')
     name.write('0')
     name.close()

     cleanOutDatabase()
     c = getContext()
     t = loader.get_template('cloudboard/index.html')
     return HttpResponse(t.render(c))
     

clusters = {'ucsd':[ "greenlight144.sysnet.ucsd.edu", "greenlight145.sysnet.ucsd.edu", "greenlight146.sysnet.ucsd.edu", "greenlight148.sysnet.ucsd.edu"],
            'oc1':["opencirrus-07501.hpl.hp.com", "opencirrus-07502.hpl.hp.com", "opencirrus-07503.hpl.hp.com", "opencirrus-07504.hpl.hp.com", "opencirrus-07505.hpl.hp.com"],
            'oc2':["opencirrus-07506.hpl.hp.com", "opencirrus-07507.hpl.hp.com", "opencirrus-07508.hpl.hp.com", "opencirrus-07509.hpl.hp.com", "opencirrus-07510.hpl.hp.com", "opencirrus-07511.hpl.hp.com"]}

def get_load_averages():

    import subprocess

    results = subprocess.Popen(['/usr/bin/gstat', '--gmond_ip=198.55.32.84','-a' ], stdout=subprocess.PIPE).communicate()[0]

    results =  results.split("\n")[11:-1]
    loads = []
    for i in range(0,len(results),2):

        name = results[i]
        data = results[i+1].split(' ')
        data = [i for i in data if i!='']
        load = data[9]
        cpu = data[0]
        loads.append((name, load, cpu,))


    ucsd = [i for i in loads if i[0] in clusters['ucsd']]
    ucsdtotal = 0
    ucsdcpu = 0
    for nodes in ucsd:
        ucsdcpu += int(nodes[2])
        load = nodes[1][:-1]
        ucsdtotal += float(load)

    oc1 = [i for i in loads if i[0] in clusters['oc1']]

    oc1total = 0
    oc1cpu = 0
    for nodes in oc1:
        oc1cpu += int(nodes[2])
        load = nodes[1][:-1]
        oc1total += float(load)
    oc2 = [i for i in loads if i[0] in clusters['oc2']]
    oc2total = 0
    oc2cpu = 0
    for nodes in oc2:
        oc2cpu += int(nodes[2])
        load = nodes[1][:-1]
        oc2total += float(load)

        
    return "ucsd " + str(ucsdtotal) + "\n" + "oc1 " + str(oc1total) + "\n" + "oc2 " + str(oc2total) + "\n"


def clusterInfo(request): 
      
      return HttpResponse(get_load_averages(), mimetype="text/plain")


def clusterSwitch(request): 
      name = open("/tmp/switch.txt",'w')
      name.write('1')
      name.close()
      return HttpResponse("Switch Triggered", mimetype="text/plain")

def clusterReset(request): 
      name = open("/tmp/switch.txt",'w')
      name.write('2')
      name.close()
      return HttpResponse("Reset Triggered", mimetype="text/plain")


def switch_status():
     try:
          name = open("/tmp/switch.txt",'r')
     except:
          return str(0)
     trigger = name.readlines()
     name.close()
     return str(trigger[0])


def clusterSwitchStatus(request): 
     return HttpResponse(switch_status(), mimetype="text/plain")
