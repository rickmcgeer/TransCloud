#!/usr/bin/env python
import dbObj
import daemon
import taskmanager
import sys, time

#
# Sample the state of each connection every five minutes and update the database to reflect it.
# Uses the Daemon class to keep-on-truckin'
#
class UpdateDaemon(daemon.Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        daemon.Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        

    def run(self):
        while True:
            db = dbObj.pgConnection()
            for site in taskmanager._sites:
                site_name =  taskmanager._sites[site]
                db.get_and_update_CGIValues(site_name)
            db.get_and_update_CGIValues('total')
            del db
            time.sleep(300)


def test_updateDaemon():
    update_daemon = UpdateDaemon('/tmp/daemon-update.pid', stdout='/tmp/update_daemon.log', stderr='/tmp/update_daemon.err')
    db = dbObj.pgConnection()
    firstValue = db.get_last_cgi_query()
    update_daemon.start()
    time.sleep(600)
    update_daemon.stop()
    secondValue = db.get_last_cgi_query()
    time.sleep(600)
    thirdValue = db.get_last_cgi_query()
    assert secondValue > firstValue, "second value %d should be > first value %d" % (secondValue, firstValue)
    assert secondValue == thirdValue, "second value %d should be = third value %d" % (secondValue, thirdValue)
    

if __name__ == "__main__":
    daemon = UpdateDaemon('/tmp/daemon-update.pid', stdout='/tmp/update_daemon.log')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
       	sys.exit(2)
            

    
