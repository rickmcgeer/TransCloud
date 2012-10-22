import os
import sys
import threading
import gcswift
import shutil
import time


# swift -A http://155.98.38.233:8080/auth/v1.0 -U system:gis -K uvicgis stat #emulab site 1
# swift -A http://142.104.195.225:8080/auth/v1.0 -U system:gis -K uvicgis stat #uvic site 2
# swift -A http://131.246.112.37:8080/auth/v1.0 -U system:gis -K uvicgis stat #glab site 3
# swift -A http://198.55.35.2:8080/auth/v1.0 -U system:gis -K uvicgis stat #geni orig! site 4


GENI_PROXY = "http://198.55.35.2:8080/auth/v1.0" # continent id 4, asia oceania
LOCAL_GENI_PROXY = "http://10.0.0.3:8080/auth/v1.0" # need diff user and pass
GENI_IMG_FILE = "swiftimages/swift-images4.txt"

UVIC_PROXY = "http://142.104.195.225:8080/auth/v1.0" # continent id 3, south america
UVIC_IMG_FILE = "swiftimages/swift-images3.txt"

GLAB_PROXY = "http://131.246.112.37:8080/auth/v1.0" # continent id 2, europe
GLAB_IMG_FILE = "swiftimages/swift-images2.txt"

EMUL_PROXY = "http://155.98.38.233:8080/auth/v1.0" # continent id 1, north america
EMUL_IMG_FILE = "swiftimages/swift-images1.txt"

SWIFT_USER = "system:gis"
SWIFT_PWD = "uvicgis"


bucketlist = []

dllist = []
dllistlock = threading.Lock()

dlfaillist = []
dlfaillistlock = threading.Lock()

uplist = []
uplistlock = threading.Lock()

upfaillist = []
upfaillistlock = threading.Lock()

imglist = []
imglistlock = threading.Lock()

alldownloadflag = 0


def download_bucket(bucket, proxy):

    status = 0

    try:
        os.mkdir(bucket)
    except OSError:
        None
    os.chdir(bucket)

    try:
        ret = gcswift.do_swift_command(proxy, "download", bucket, 1)
        print ret.communicate()[0]
        uplistlock.acquire()
        uplist.append(bucket)
        uplistlock.release()
    except AssertionError:
        print "failed to download bucket!"
        dlfaillistlock.acquire()
        dlfaillist.append(bucket)
        dlfaillistlock.release()
        status = -1

    os.chdir('..')
    
    return status


def dl_thread():

    print "Download thread started"

    while len(dllist): # dont get the lock as we just read

        if len(uplist) > 5:
            time.sleep(8) # sleep if the upload list is large, so we can get rid of some temp files

        dllistlock.acquire()
        bucket = dllist.pop()
        dllistlock.release()
        if bucket:
            download_bucket(bucket, ORIG_PROXY)

    print "Download thread finished"


def upload_bucket(bucket, proxy):

    status = 0

    os.chdir(bucket)

    try:
        ret = gcswift.do_swift_command(proxy, "upload", bucket, 1, "*")
        print ret.communicate()[0]

    except AssertionError:
        print "failed to upload bucket!"
        upfaillistlock.acquire()
        upfaillist.append(bucket)
        upfaillistlock.release()
        status = -1

    try:
        os.chdir('..')
        shutil.rmtree(bucket)
    except OSError:
        print "Failed to remove temp dir", bucket

    return status


def up_thread():

    print "Upload thread started"

    while not alldownloadflag or len(uplist):

        if not len(uplist):
            time.sleep(20) # sleep for 20 seconds

        uplistlock.acquire()
        bucket = uplist.pop()
        uplistlock.release()
        if bucket:
            upload_bucket(bucket, NEW_PROXY)

    print "Upload thread finished"


def swift_transfer(dlproxy, upproxy, imglistfile):

    f = open(imglistfile)
    
    imgsfromdb = [line.strip() for line in f.readlines()]

    # dlthreadlist = []
    # upthreadlist = []
    # global alldownloadflag
    # alldownloadflag = 0

    try:
        ret = gcswift.do_swift_command(upproxy, "list", "", 1)
        bucketlist = ret.communicate()[0].split()
    except AssertionError:
        print "failed to get list of existing buckets"

    imglist = []
    dllist = []
    dlfaillist = []
    uplist = []
    upfaillist = []
    

    imglistlock.acquire()
    dllistlock.acquire()
    
    for img in imgsfromdb:
        nameparts = img.split('_')
        
        # dont do bad entries that dont have a 'p' in them
        if 'p' in nameparts[0]:
            img = nameparts[0]+'_'+nameparts[1]+'.'+nameparts[2]+'.'+nameparts[3]+'.tif.gz'
            imglist.append(img)
            bucket = nameparts[0]
            if bucket not in dllist and bucket not in bucketlist:
                dllist.append(bucket)

    imglistlock.release()
    dllistlock.release()

    # make sure we have/are in our temp dir
    try:
        os.mkdir('/tmp/swiftdist/')
    except OSError:
        print "temp swift dir already exists!"
    os.chdir('/tmp/swiftdist/')


    # screw the threading it doesnt work like i though it would
    for b in dllist:
        try:
            download_bucket(b, dlproxy)
            if b in uplist:
                upload_bucket(b, upproxy)
        except Exception as e:
            print e


    # # create download thread
    # dt = threading.Thread(target=dl_thread())
    # dlthreadlist.append(dt)

    # # create upload thread
    # ut = threading.Thread(target=up_thread())
    # upthreadlist.append(ut)

    # # start threads
    # for dt in dlthreadlist:
    #     dt.start()
    # for ut in upthreadlist:
    #     ut.start()

    # # wait for threads to terminate
    # for dt in dlthreadlist:
    #     dt.join()
    #     alldownloadflag = 1
    # for ut in upthreadlist:
    #     ut.join()


    print "FAILED DOWNLOADS"
    print dlfaillist

    print "FAILED UPLOADS"
    print upfaillist


if __name__ == "__main__":

    swift_transfer(GENI_PROXY, EMUL_PROXY, EMUL_IMG_FILE)
    swift_transfer(GENI_PROXY, UVIC_PROXY, UVIC_IMG_FILE)
    swift_transfer(GENI_PROXY, GLAB_PROXY, GLAB_IMG_FILE)

