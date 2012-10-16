import glob
import os
import subprocess
import threading
import time
import decimal
import threadpool
import sys


class LandsatFile:

    def _get_pathparts(self, filepath):
        parts = self.filename.split('_')
        self.pathrow = parts[0]
        dateband = parts[1].split('.SR.')
        self.date = dateband[0]
        self.band = dateband[1][:-7]

    def __init__(self, path, size):
        self.path = path
        self.location, self.filename = os.path.split(path)
        self.size = size
        self._get_pathparts(path)

    def __str__(self):
        return self.pathrow + " " + self.date + " " + self.band


def crawl_filesystem(searchpath, pattern="*.gz"):
    for path in searchpath:
        for subpath, subdirs, files in os.walk(path):
            for match in glob.glob(os.path.join(subpath, pattern)):
                yield match


def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0


def filter(path):
    filename = os.path.basename(path)
    if '.SR.b' in filename:
        if '.SR.b07' in filename \
               or '.SR.b04' in filename \
               or '.SR.b03' in filename:
            return True
    return False


def upload_single_landsat(lsat):
    program = "swift"

    command = [program, "-A",
               "http://newswift.gcgis.trans-cloud.net:8080/auth/v1.0",
               "-U",
               "system:gis",
               "-K",
               "uvicgis",
               "upload",
               "-c",
               lsat.pathrow, lsat.filename]
    # command = ["ln", "-s", lsat.path, "/home/cmatthew/tmp/ls/"+lsat.filename]
    return subprocess.call(command, cwd=lsat.location)


#targets = ["/media/GEODATA/glc_landsat/GLCF.TSM.AZ-002.00.GLS2005/WRS2/"]
targets = ["/mnt/nasy/Landsat7/GLS2005/WRS2/",\
           "/media/GEODATA/glc_landsat/GLCF.TSM.AZ-002.00.GLS2005/WRS2/"]
sizelock = threading.Lock()
total_size = 0
orig_size = 0
to_upload = []


sizelock.acquire()
print "Phase 1: Reading files"
for f in crawl_filesystem(targets):
    if not filter(f):
        continue
    size = os.path.getsize(f)
    total_size += size
    to_upload.append(LandsatFile(f, size))

# are we going to start in the middle?
spot = 0
if len(sys.argv) > 1:
    skip = sys.argv[1]
    for ls in enumerate(to_upload):
        if ls[1].pathrow == skip:
            spot = ls[0]
            break

if len(sys.argv) > 1 and spot == 0:
    print "Warning: didn't find restore point."
new_size = 0
for ls in to_upload[:spot]:
    new_size += ls.size
to_upload = to_upload[spot:]
total_size = total_size - new_size
 
orig_size = total_size
starttime = time.time()

print sizeof_fmt(total_size)
nfiles = len(to_upload)
ndone = 0
print nfiles
sizelock.release()

print "Phase 2: Uploading"
decimal.getcontext().prec = 4
#for landsat in to_upload:
#    upload_single_landsat(landsat)


def done(job, rc):
    global total_size, sizelock, ndone
    sizelock.acquire()

    total_size -= job.args[0].size
    ndone += 1
    sizelock.release()
    currtime = time.time()
    elapsed = currtime - starttime

    print "Remaining:", sizeof_fmt(total_size), \
          "Speed:", sizeof_fmt((orig_size - total_size) / (elapsed)), \
          "/s", (decimal.Decimal(ndone) / decimal.Decimal(nfiles)) * 100, "%"

    if rc != 0:
        print "Error: failed to upload", job.args[0].filename


pool = threadpool.ThreadPool(10)
requests = threadpool.makeRequests(upload_single_landsat, to_upload, done)
[pool.putRequest(req) for req in requests]
pool.wait()
