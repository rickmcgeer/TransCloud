import glob
import os
import subprocess
import threading
import time
import decimal
import threadpool


class LandsatFile:
    def _get_pathparts(self, filepath):
        parts = self.filename.split('_')
        self.pathrow =  parts[0]
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
 



def crawl_filesystem(searchpath, pattern = "*.gz"):
    for path in searchpath:
        for subpath, subdirs, files in os.walk(path):
            for match in glob.glob(os.path.join(subpath,pattern)):
                yield match

def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0

def filter(path):
    filename = os.path.basename(path)
    if '.SR.b' in filename:
        if '.SR.b07' in filename or '.SR.b04' in filename or '.SR.b03' in filename:
            return True
    return False

# https://198.55.37.2:8080/auth/v1.0 -U system:gis -K uvicgis upload myfiles bigfile2.tgz
def upload_single_landsat(lsat):
    command = ["swift", "-A",
               "https://10.0.0.3:8080/auth/v1.0",
               "-U",
               "system:gis",
               "-K",
               "uvicgis",
               "upload",
               "-c",
               lsat.pathrow, lsat.filename]
    # command = ["ln", "-s", lsat.path, "/home/cmatthew/tmp/ls/"+lsat.filename]


    bucket = lsat.pathrow

    return subprocess.call(command, cwd=lsat.location)


#targets = ["/media/GEODATA/glc_landsat/GLCF.TSM.AZ-002.00.GLS2005/WRS2/"]
targets = ["/media/GEODATA/glc_landsat/GLCF.TSM.AZ-002.00.GLS2005/WRS2/",
                           "/mnt/nasy/Landsat7/GLS2005/WRS2/"]
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
          "Speed:",sizeof_fmt((orig_size - total_size) / (elapsed)), \
          "/s", (decimal.Decimal(ndone)/decimal.Decimal(nfiles))*100, "%"
    
    if rc != 0:
        print "Error: failed to upload", job.args[0].filename


pool = threadpool.ThreadPool(10)
requests = threadpool.makeRequests(upload_single_landsat, to_upload, done)
[pool.putRequest(req) for req in requests]
pool.wait()

