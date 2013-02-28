import sys, time
from daemon import Daemon
from mq_process_results import *

class CalcDaemon(Daemon):
	def run(self):
		process_results(blocking=True)

if __name__ == "__main__":
	daemon = CalcDaemon('/tmp/daemon-calc.pid', stdout='/tmp/calc_daemon.log')
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
