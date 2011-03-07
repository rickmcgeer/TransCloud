from jobs.models import newJob
import datetime
import random

urls=["foo.com", "bar.com", "baz.com", "ucsd.edu", "hp.com",
      "northwestern.edu", "geni.net", "princeton.edu", "uvic.ca",
      "uic.edu"]

videos = ["foo.mp4", "bar.mp2", "baz.flv", "theplay.avi", "map_anim.flv",
          "foo.mp2", "bar.mp4", "baz.mp4", "theplay.mp4", "map2.flv"]

def generateRandomURL():
    return 'http://www.%s/%s' % (random.choice(urls), random.choice(videos))

users = ["rick.mcgeer@hp.com", "alvina@cs.ucsd.edu", "marcoy@uvic.ca",
         "llp@cs.princeton.edu", "celliot@bbn.com"]

domains = ["198.55.37", "198.37.9", "16.25.12", "17.32.8"]

def genRandomServer():
    domain = random.choice(domains)
    node = random.randint(1, 32)
    return "%s.%d" % (domain, node)

def genRandomStartDate():
    now = datetime.datetime.now()
    delta = random.randint(1000,86400)
    timeDelta = datetime.timedelta(0, delta)
    return now - timeDelta

def genRandomEndDate(startDate):
    delta = random.randint(1000,86400)
    timeDelta = datetime.timedelta(0, delta)
    return startDate + timeDelta

def genRandomOffset():
    now = datetime.datetime.now()
    delta = random.randint(0, 1000)
    timeDelta = datetime.timedelta(0, delta)
    return now - timeDelta


def createRandomJobList(numJobs = 1000):
    result = []
    jobPrefix = "job_%d" % random.randint(0, 1000)
    for i in range(0, numJobs):
        completed = random.randint(0, 100) < 10
        if completed:
            startDate = genRandomStartDate()
            endDate = genRandomEndDate(startDate)
        else:
            startDate = genRandomOffset()
            endDate = datetime.datetime.now()
        name = "%s_%d" % (jobPrefix, i)
        server = genRandomServer()
        user = random.choice(users)
        options = "-s 1280x724"
        source = generateRandomURL()
        result.append((name, server, user, source, options, startDate, completed, endDate))
    return result
