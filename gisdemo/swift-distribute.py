import os
import sys
import threading
import gcswift
import shutil
import time



UVIC_PROXY = "http://142.104.195.225:8080/auth/v1.0"
NW_PROXY = "http://165.124.51.144:8080/auth/v1.0"


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


def swift_transfer(dlproxy, upproxy, imglistfile=None):

    if imglistfile:
        f = open(imglistfile)
    
        imgsfromdb = [line.strip() for line in f.readlines()]
    else:
        try:
            # for some reason we cant list the whole repo, we time out 
            #  on the command line and i have no idea why
            ret = gcswift.do_swift_command(dlproxy, "list -p p0", "", 1)
            imgsfromdb = ret.communicate()[0].split()

            ret = gcswift.do_swift_command(dlproxy, "list -p p1", "", 1)
            imgsfromdb += ret.communicate()[0].split()

            ret = gcswift.do_swift_command(dlproxy, "list -p p2", "", 1)
            imgsfromdb += ret.communicate()[0].split()
        except AssertionError as e:
            print "failed to get img list:", str(e)
            sys.exit()

    # dlthreadlist = []
    # upthreadlist = []
    # global alldownloadflag
    # alldownloadflag = 0

    try:
        ret = gcswift.do_swift_command(upproxy, "list", "", 1)
        bucketlist = ret.communicate()[0].split()
    except AssertionError:
        print "failed to get list of existing buckets:", str(e)
        sys.exit()

    imglist = []
    dllist = []
    dlfaillist = []
    uplist = []
    upfaillist = []
    


    imglistlock.acquire()
    dllistlock.acquire()
    
    for bucket in imgsfromdb:
        
        if 'p' in bucket:
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
            dlfailed = download_bucket(b, dlproxy)
            if not dlfailed:
                upfailed = upload_bucket(b, upproxy)
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

    swift_transfer(UVIC_PROXY, NW_PROXY)

