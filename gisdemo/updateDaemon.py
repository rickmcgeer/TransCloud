#!/usr/bin/env python
import dbObj
import daemon
import mq.taskmanager
import sys, time

#
# Sample the state of each connection every five minutes and update the database to reflect it.
# Uses the Daemon class to keep-on-truckin'
#
class UpdateDaemon(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        self.db = dbObj.pgConnection()

    def run(self):
        while True:
            for site in mq.taskmanager._sites:
                site_name =  mq.taskmanager._sites[site]
                self.db. get_and_update_CGIValues(site_name)
            self.db. get_and_update_CGIValues('total')
            sleep(300)

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
            

    
