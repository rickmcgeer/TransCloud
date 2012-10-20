import os
import sys
import signal
import commands
import subprocess
import settings
import optparse


class Alarm(Exception):
    pass


def alarm_handler(signum, frame):
    raise Alarm


def do_swift_command(swift_proxy, operation, bucket, *args):
  command = "swift -A "+swift_proxy+" -U "+settings.SWIFT_USER+ \
    " -K "+settings.SWIFT_PWD+ " " + \
    operation + " " + \
    bucket + " " + \
    ' '.join(args)

  print command

  p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, preexec_fn=os.setsid)

  try:
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(3*60)  # we will timeout after 3 minutes 

    p.wait()
    signal.alarm(0)  # reset the alarm
  except Alarm:
    os.killpg(p.pid, signal.SIGTERM)
    # raise an assertion so we can continue execution after 
    #  (should really have our own exception but fk it)
    raise AssertionError("Timeout gettimg images from swift")

  return p


DEFAULT_SWIFT_HOST = "198.55.35.2"

def swift(operation, bucket, *args):
  """operation: upload, download
  bucket: bucket number
  args: files needed to download
  """
  parser = optparse.OptionParser()
  parser.add_option("-s", "--swift_host", dest="swift_host", type="string", default=DEFAULT_SWIFT_HOST, help="hostname or ip of the swift server")
  (options, args_not_used) = parser.parse_args()
  print "Using swift proxy http://"+options.swift_host+":8080/auth/v1.0"

  process = do_swift_command("http://"+options.swift_host+":8080/auth/v1.0", operation, bucket, *args)
  if process.returncode != 0 and options.swift_host != DEFAULT_SWIFT_HOST:
    print "Failed on swift host %s with %s, trying on %s" % (options.swift_host, process.communicate()[1], DEFAULT_SWIFT_HOST)
    process = do_swift_command(settings.SWIFT_PROXY, operation, bucket, *args)
  assert process.returncode == 0, "Failed on swift host %s with %s" % (DEFAULT_SWIFT_HOST, process.communicate()[1])


if __name__ == '__main__':   
  swift("download", "p233r094", 'p233r094_7dt20040310.SR.b03.tif.gz', 'p233r094_7dt20040310.SR.b04.tif.gz')
