import os
import sys
import signal
import commands
import subprocess
import settings
import shutil
import time
from subprocess import check_call
import tempfile
import stat
import taskmanager


class SwiftFailure(Exception):
    def __init__(self, message, swift_url):
        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)
        # Now for your custom code...
        self.swift_url = swift_url

class MissingSwiftFile(SwiftFailure):
   def __init__(self, message, swift_url):
        # Call the base class constructor with the parameters it needs
        SwiftFailure.__init__(self, message, swift_url)





class Alarm(Exception):
    pass


def alarm_handler(signum, frame):
    raise Alarm

def _to_proxy_url(ip):
    return "http://" + ip + ":8080/auth/v1.0"

def do_swift_command(swift_proxy, swift_user, operation, bucket, timeout, *args):

  if type(args) == list or type(args)==tuple:
      args = ' '.join(args)
  if "http://" not in swift_proxy:
      swift_proxy = _to_proxy_url(swift_proxy)

  command = "swift -A " + swift_proxy + " -U " + swift_user + \
    " -K " + settings.SWIFT_PWD + " " + \
    operation + " " + \
    bucket + " " + \
    args
  # print command
  # spawn a shell that executes swift, we set the sid of the shell so
  #  we can kill it and all its children with os.killpg
  p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, preexec_fn=os.setsid)

  if timeout:
    try:
      signal.signal(signal.SIGALRM, alarm_handler)
      signal.alarm(3*60)  # we will timeout after 3 minutes 

      (out, err) = p.communicate()
      signal.alarm(0)  # reset the alarm
    except Alarm:
      os.killpg(p.pid, signal.SIGTERM)
      # raise an assertion so we can continue execution after 
      #  (should really have our own exception but fk it)
      raise SwiftFailure("Timeout "+operation+"ing swift images", command)
  else:
      (out, err) = p.communicate()

  return p, out, err



def swift(operation, bucket, *args):
  """operation: upload, download
  bucket: bucket number
  args: files needed to download
  """
  # if the image is migging, upload it
  cache = False
  process, out, err = do_swift_command(_to_proxy_url(settings.SWIFT_PROXY1), \
                                 settings.SWIFT_USER, operation, bucket, True, *args)
  if process.returncode != 0:
    message = err
    print "Warning: Failed on swift host %s with %s, trying on %s" % \
        (settings.SWIFT_PROXY1, message, settings.SWIFT_PROXY2)
    if operation == "download" and "Object" in message and "not found" in message:
        cache = True


    process, out, err = do_swift_command(_to_proxy_url(settings.SWIFT_PROXY2), settings.SWIFT_BACKUP_USER, operation, bucket, True, *args)
    if process.returncode != 0:
        message = err
        if operation == "download" and "Object" in message and "not found" in message:
            raise MissingSwiftFile(message, _to_proxy_url(settings.SWIFT_PROXY2))
        else:
            raise SwiftFailure(message, _to_proxy_url(settings.SWIFT_PROXY2))

def test_gcswift():
    os.chdir(settings.IMG_TMP)
    fn = 'p104r015_5dt20070726.SR.b03.tif.gz'
    try:
        swift("download", "p104r015", fn, fn)
        assert os.path.exists(fn), "File was not created"
        assert os.path.getsize(fn) > 1000000, "File is not very big!"
        swift("download", "p104r015", fn+'.md5', fn+'.md5')
        assert os.path.exists(fn+'.md5'), "MD5 File was not created"
        assert os.path.getsize(fn+'.md5') > 10, "MD5 File is not very big!"

        try:
            check_call(["md5sum","-c",fn+".md5"])
        except OSError:
            pass # md5sum command is not found
    finally:
        os.unlink(fn)
        os.unlink(fn+'.md5')


# def test_diskspace():
#     """Check that we have about the right amount of free disk space"""
#     os.chdir(settings.IMG_TMP)
#     fil = open("big_tmp_file", 'w')

#     for i in xrange(0, 1024*1024*1024*10, 4096):
#         fil.write('x'*4096)
#     fil.close()
#     os.unlink("big_tmp_file")
    

def test_all_images():
    """Check that every path has at least one row bucket"""
    from warnings import warn
    return
    paths =  "p091 p098 p105 p112 p119 p126 p133 p140 p147 p154 p161 p168 p175 p182 p189 p196 p203 p210 p217 p224 p231 p092 p099 p106 p113 p120 p127 p134 p141 p148 p155 p162 p169 p176 p183 p190 p197 p204 p211 p218 p225 p232 p093 p100 p107 p114 p121 p128 p135 p142 p149 p156 p163 p170 p177 p184 p191 p198 p205 p212 p219 p226 p233 p094 p101 p108 p115 p122 p129 p136 p143 p150 p157 p164 p171 p178 p185 p192 p199 p206 p213 p220 p227 p095 p102 p109 p116 p123 p130 p137 p144 p151 p158 p165 p172 p179 p186 p193 p200 p207 p214 p221 p228 p096 p103 p110 p117 p124 p131 p138 p145 p152 p159 p166 p173 p180 p187 p194 p201 p208 p215 p222 p229 p097 p104 p111 p118 p125 p132 p139 p146 p153 p160 p167 p174 p181 p188 p195 p202 p209 p216 p223 p230"
    for p in paths.split(" "):
        for r in xrange(1,248):
            bucket = "%sr%03d"%(p,r)
            print bucket
            try:
                swift("stat", bucket)
            except MissingSwiftFile:
                continue
            else:
                break
            warn("Path %s has no rows"%(p))

#
# List files by access time.  Given a directory, return a list of triples
# (access_time, file_name, size), sorted in increasing order by access time.  This
# probably needs more error-checking, where file_name is fully qualified (e.g., /tmp/foo, not foo)
# and size is in bytes
#
def files_by_access_time(dir):
    files = os.listdir(dir)
    file_list_by_atime = []
    for file_name in files:
        full_file_name = dir + "/" + file_name
        file_info = os.lstat(full_file_name)
        file_list_by_atime.append((file_info.st_atime, full_file_name, file_info.st_size))
    return sorted(file_list_by_atime, key=lambda file_tuple: file_tuple[0])

#
# Clear at least size_to_clear bytes from a directory, Least-Recently-Used
# Uses files_by_access_time to get the list.  Note file_list_by_atime is returned by
# files_by_access_time.  Note size_to_clear should be in BYTES.
# 
#
def clear_room_in_dir(dir, size_to_clear, file_list_by_atime = None):
    if not file_list_by_atime:
        file_list_by_atime = files_by_access_time(dir)
    size_cleared = 0
    for (atime, full_file_name, size) in file_list_by_atime:
        try:
            os.remove(full_file_name)
            size_cleared = size_cleared + size
        except OSError:
            continue
        if size_cleared >= size_to_clear:
            return

#
# get the total size of a directory.  returns in BYTES
#
def get_dir_size(dir, file_list_by_atime = None):
    if not file_list_by_atime:
        file_list_by_atime = files_by_access_time(dir)
    total_size = 0
    for (atime, full_file_name, size) in file_list_by_atime:
        total_size = total_size + size
    return total_size

#
# A class is probably overkill here, but it organizes the code nicely...
#
class FileCache:
    def __init__(self, directory=settings.file_cache_directory, max_size_in_kbytes = settings.file_cache_size_in_kbytes):
        self.directory = directory
        self.max_size_in_kbytes = max_size_in_kbytes
        if(not os.path.exists(self.directory)):
            try:
                os.mkdir(self.directory)
            except OSError:
                print "Failed to create directory " +  self.directory + " and it does not exist"
        try:
            os.chmod(self.directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except OSError:
            print "Failed to change mode of " + self.directory + " to 777"
        self.file_whitelist = []

    def download_special_case_tokyo(self, bucket, file_name):
        special_tokyo_command = "/usr/bin/imq_req2 " + bucket + file_name
        p = subprocess.Popen(special_tokyo_command,  shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        return self.directory + "/" + file_name
        

    #
    # get and cache a file, and return the file descriptor to the open file, suitable for reading
    # returns None if the directory doesn't exist, or we couldn't download the file, or we couldn't
    # open it
    #

    def get_file(self, bucket, file_name):
        file_path = self.directory + "/" + file_name
        if(not os.path.exists(self.directory)):
            print "Directory ", self.directory, " does not exist"
            return None
        if taskmanager.get_local_site_name() == 'u-tokyo.ac.jp':
            return self.download_special_case_tokyo(bucket, file_name)
        if os.path.exists(self.directory + "/" + file_name):
            # set the path's utime so LRU's don't get it
            os.utime(file_path, None)
        else:
            os.chdir(self.directory) # so swift downloads to the right directory
            swift("download", bucket, file_name, file_name)
            if (not os.path.exists(file_path)):
                print "File " + file_name + " was not downloaded from swift from bucket " + bucket
                return None
            else:
                os.chmod(file_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                
        self.file_whitelist.append(file_path)
        return file_path
        ## file_handle = open(file_path, "rb")
        ## if file_handle == None:
        ##     print "Failed to open " + file_path
        ##     return None
        ## return file_handle

    #
    # clear the cache down to max_size_in_kbytes, least-recently-used.
    #

    def cleanup_cache(self, respect_file_whitelist = False):
        if taskmanager.get_local_site_name() == 'u-tokyo.ac.jp':
            os.unlink(self.directory)
            os.mkdir(self.directory)
            try:
                os.chmod(self.directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            except OSError:
                print "Failed to change mode of " + self.directory + " to 777"
            return
        files_by_atime = files_by_access_time(self.directory)
        max_size_in_bytes = self.max_size_in_kbytes << 10 # convert from kbytes to bytes
        total_size = get_dir_size(self.directory, files_by_atime)
        if (total_size <= max_size_in_bytes): return
        if respect_file_whitelist:
            files_to_comb = []
            for (atime, filepath, size) in files_by_atime:
                if not (filepath in self.file_whitelist):
                    files_to_comb.append((atime, filepath, size))
        else: files_to_comb = files_by_atime
        clear_room_in_dir(self.directory, total_size - max_size_in_bytes, files_to_comb)

    # returns true iff file (not qualified: foo instead of /tmp/foo) is in cache

    def in_cache(self, file):
        return os.path.exists(self.directory + "/" + file)

    def clear_whitelist(self):
        self.file_whitelist = []

    
        
            
            

def rm_error(function, path, excinfo):
    print "failed to remove directory " + settings.file_cache_directory + ". Error on path " + path
#
# preconditions: bucket test_file_cache has 10 files, file_1...file_10, where
# file i is of size i * 1024 bytes, and 
#
        
        
def test_file_cache():
    # Clean up the directory if it exists
    if os.path.exists(settings.file_cache_directory):
        shutil.rmtree(settings.file_cache_directory, rm_error) 
    file_cache = FileCache(max_size_in_kbytes = 5) # small for testing

    # initial experiment...
    files_to_download = ['file_1', 'file_2', 'file_3']

    # download them, with a 20 second break between each one

    for file_name in files_to_download:
        foo = file_cache.get_file('test_file_cache', file_name)
        if (not foo):
            print "Test 1: No file path returned for file " + file_name
        time.sleep(20) # sleep for a bit to get a spread on the access time

    # each should be in the cache

    for file_name in files_to_download:
        if not(file_cache.in_cache(file_name)):
            print  "Test 1: No file " + file_name + " in cache"

    file_cache.cleanup_cache()

    #
    # files 2 and 3 should be in the cache, file 1 out
    #
    for file_name in ['file_2', 'file_3']:
        if not(file_cache.in_cache(file_name)):
            print  "Test 2: No file " + file_name + " in cache"

    if file_cache.in_cache('file_1'):
        print "Test 1: File file_1 not removed from cache"

    #
    # clean the whitelist for a new download
    #

    file_cache.clear_whitelist()
    foo = file_cache.get_file('test_file_cache', 'file_4')
    if not (file_cache.in_cache('file_4')):
        print 'Test 3: File file_4 not in cache'

    file_cache.cleanup_cache(respect_file_whitelist = True)

    #
    # files 2 and 3 should not be in the cache, file 4 in
    #

    if not (file_cache.in_cache('file_4')):
        print 'Test 4: File file_4 not in cache'

    for file_name in ['file_2', 'file_3']:
        if file_cache.in_cache(file_name):
            print  "Test 4: File " + file_name + " in cache"
     

def get_raw_file_name(fname):
    return (fname.split("/"))[-1]

def get_dir_name(fname):
    return "/".join(fname.split("/")[0:-1])

def errorhandler(function, path, execinfo):
    log('Failed to remove temp directory ' + path)
         
     
class FileManager:
    def __init__(self):
        self.file_cache = FileCache()
        self.tmp_file_dir=tempfile.mkdtemp(dir=settings.TEMP_FILE_DIR)
        try:
            os.chmod(self.tmp_file_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except OSError:
            print "Failed to change mode of " + self.tmp_file_dir + " to 777"
        self.shapefile_tmpDir = self.tmp_file_dir + "/tmp"

    def get_file(self, bucket, file_name):
        return self.file_cache.get_file(bucket, file_name)

    def get_tiff_name(self, file_name):
        raw_file_name = get_raw_file_name(file_name)
        tiff_file_name = raw_file_name.rstrip('.gz')
        return self.tmp_file_dir + "/" + tiff_file_name

    def cleanup(self):
        self.file_cache.cleanup_cache()
        shutil.rmtree(self.tmp_file_dir, onerror=errorhandler)
 
