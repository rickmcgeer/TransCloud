import os
import sys
import threading
import swift
import shutil
import time

ORIG_PROXY = "http://198.55.35.2:8080/auth/v1.0"
NEW_PROXY = "http://155.98.38.233:8080/auth/v1.0"

SWIFT_USER = "system:gis"
SWIFT_PWD = "uvicgis"


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

# swift -A http://155.98.38.233:8080/auth/v1.0 -U system:gis -K uvicgis stat #emulab site 1
# swift -A http://142.104.195.225:8080/auth/v1.0 -U system:gis -K uvicgis stat #uvic site 2
# swift -A http://131.246.112.37:8080/auth/v1.0 -U system:gis -K uvicgis stat #glab site 3
# swift -A http://198.55.35.2:8080/auth/v1.0 -U system:gis -K uvicgis stat #geni orig! site 4


def download_bucket(bucket, proxy):

    try:
        os.mkdir(bucket)
    except OSError:
        None
    os.chdir(bucket)

    try:
        ret = swift.do_swift_command(proxy, "download", bucket)
        print ret.communicate()[0]
        uplistlock.acquire()
        uplist.append(bucket)
        uplistlock.release()
    except AssertionError:
        print "failed to download bucket!"
        dlfaillistlock.acquire()
        dlfaillist.append(bucket)
        dlfaillistlock.release()

    os.chdir('..')


def dl_thread():

    while len(dllist): # dont get the lock as we just read

        if len(uplist) > 5:
            time.sleep(8) # sleep if the upload list is large, so we can get rid of some temp files

        dllistlock.acquire()
        bucket = dllist.pop()
        dllistlock.release()
        if bucket:
            download_bucket(bucket, ORIG_PROXY)



def upload_bucket(bucket, proxy):

    os.chdir(bucket)

    try:
        ret = swift.do_swift_command(proxy, "upload", bucket, "*")
        print ret.communicate()[0]

    except AssertionError:
        print "failed to upload bucket!"
        upfaillistlock.acquire()
        upfaillist.append(bucket)
        upfaillistlock.release()

    try:
        os.chdir('..')
        shutil.rmtree(bucket)
    except OSError:
        print "Failed to remove temp dir", bucket


def up_thread():

    while not alldownloadflag or len(uplist):

        if not len(uplist):
            time.sleep(8) # sleep for 8 seconds

        uplistlock.acquire()
        bucket = uplist.pop()
        uplistlock.release()
        if bucket:
            upload_bucket(bucket, NEW_PROXY)



if __name__ == "__main__":

    imglistfile = sys.argv[1]

    f = open(imglistfile)
    
    imgsfromdb = [line.strip() for line in f.readlines()]

    dlthreadlist = []
    upthreadlist = []
    global alldownloadflag

    imglistlock.acquire()
    dllistlock.acquire()
    
    for img in imgsfromdb:
        nameparts = img.split('_')
        
        # dont do bad entries that dont have a 'p' in them
        if 'p' in nameparts[0]:
            img = nameparts[0]+'_'+nameparts[1]+'.'+nameparts[2]+'.'+nameparts[3]+'.tif.gz'
            imglist.append(img)
            bucket = nameparts[0]
            if bucket not in dllist:
                dllist.append(bucket)

    imglistlock.release()
    dllistlock.release()

    # make sure we have/are in our temp dir
    try:
        os.mkdir('/tmp/swiftdist/')
    except OSError:
        print "temp swift dir already exists!"
    os.chdir('/tmp/swiftdist/')


    # screw the threading it doesnt alternate like i though it would
    for b in dllist:
        download_bucket(b)
        upload_bucket(b)


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
    #     dtt.join()
    #     alldownloadflag = 1
    # for ut in upthreadlist:
    #     ut.join()


    print "FAILED DOWNLOADS"
    print dlfaillist

    print "FAILED UPLOADS"
    print upfaillist
