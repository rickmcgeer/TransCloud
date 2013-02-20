import settings
import sys
import datetime
LOG_FILE = None

prefix = ""

def start():
    global LOG_FILE
    try:
        LOG_FILE = open(settings.LOG_NAME, 'w')
    except IOError as e:
        print "Failed to open Log:", e, "\nLogging to stderr"
        LOG_FILE = sys.stderr

    
def close():
    global LOG_FILE
    log("Stopping logging")
    LOG_FILE.close()


def log(*args):
    """ Write a timestamp and the args passed to the log. 
    If there is no log file we treat stderr as our log
    """
    global LOG_FILE
    str_args = " ".join([str(x) for x in args])
    print prefix +" "+ str_args
    if LOG_FILE:
        msg = str(datetime.datetime.now()) + ": " + prefix + ": " + str_args
        
        LOG_FILE.write(msg)
            
        if msg[-1] != "\n":
            LOG_FILE.write("\n")


