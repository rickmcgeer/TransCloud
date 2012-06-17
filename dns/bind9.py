#!/usr/bin/python

#write out new zone db
import subprocess
import time
import os
import syslog


# some functions to help us log to syslog
# then if stuff doesnt work we have a log!
LOG_PREFIX = "[GENICloud DNS] "


def _syslog(level, message):
    """Print a message to syslog and screen"""
    message = str(message)
    print message
    syslog.syslog(level, LOG_PREFIX + message)


def log(message):
    """Print a info level log message."""
    _syslog(syslog.LOG_INFO, message)


def warning(msg):
    """Print a warning level log message."""
    _syslog(syslog.LOG_WARN, msg)


def error(msg):
    """Print an Error level log message"""
    _syslog(syslog.LOG_ERR, msg)


# Bind9 template
template = """
;
; BIND data file for local loopback interface
;
$TTL	604800
@	IN	SOA	ns.genicloud.trans-cloud.net. root.genicloud.trans-cloud.net. (
            %d		; Serial
            604800		; Refresh
            86400		; Retry
            2419200		; Expire
            604800 )	; Negative Cache TTL
;
@	IN	NS	localhost.
@	IN	A	50.92.210.3
@	IN	AAAA	::1
test	IN	A	1.2.3.4
foo.bar	IN	CNAME	test
"""


# where is the names database stored?
NAMESLIST_FILENAME = "genicloud_dns_names"
NAMESLIST_PATH = "/etc/" + NAMESLIST_FILENAME


def pull_dns_list():
    """ Pull the names list from the slice manager server.
    It is stored in a file in /etc. SCP it here, so we can
    use it.
    """
    try:
        os.remove(NAMESLIST_FILENAME)
    except OSError:
        log("Did not find" + NAMESLIST_FILENAME + "to remove.")

    # this assumes the ssh_config user file is setup with an oc1 entry
    command = "scp oc1:" + \
              NAMESLIST_PATH + " ."

    rc = subprocess.call(command, shell=True)
    if rc != 0:
        raise Exception("Something went wrong scping the names file.")
    else:
        print "Got file", NAMESLIST_FILENAME


def make_names_list():
    """ take the names list file and make a the names list out of it"""
    f = open(NAMESLIST_FILENAME, 'r')

    # get lines, remove newlines etc
    lines = [line.strip() for line in f.readlines()]
    # remove blank lines
    lines = [x for x in lines if x != '']
    # remove comments
    lines = [x.strip() for x in lines if x[0] != '#']

    # put each entry into a tuple
    names = [tuple(x.split(" ")) for x in lines]

    return names


def make_string(mappings):
    s = template % (time.time())
    for host in mappings:
        s = s + "%s\tIN\tA\t%s\n" % (host[0], host[1])
    return s


def write_out(mapping):
    s = make_string(mapping)
    try:
        f = open("/etc/bind/db.genicloud.trans-cloud.net", "w")
        f.write(s)
        f.close()
    except Exception, e:
        print s
        raise Exception("failed to write the zones database:\n" + str(e))
    rc = subprocess.call(["/usr/sbin/rndc", "reload"])
    if rc != 0:
        raise Exception("rndc failed with: " + str(rc))


if __name__ == "__main__":
    try:
        pull_dns_list()
        mappings = make_names_list()
        write_out(mappings)
    except Exception, e:
        error("program failed: " + str(e))
