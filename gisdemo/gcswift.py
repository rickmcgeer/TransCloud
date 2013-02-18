import os
import sys
import signal
import commands
import subprocess
import settings


class Alarm(Exception):
    pass


def alarm_handler(signum, frame):
    raise Alarm

def _to_proxy_url(ip):
    return "http://" + ip + ":8080/auth/v1.0"

def do_swift_command(swift_proxy, operation, bucket, timeout, *args):

  if type(args) == list or type(args)==tuple:
      args = ' '.join(args)
  if "http://" not in swift_proxy:
      swift_proxy = _to_proxy_url(swift_proxy)

  command = "swift -A " + swift_proxy + " -U " + settings.SWIFT_USER + \
    " -K " + settings.SWIFT_PWD + " " + \
    operation + " " + \
    bucket + " " + \
    args

  # spawn a shell that executes swift, we set the sid of the shell so
  #  we can kill it and all its children with os.killpg
  p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, preexec_fn=os.setsid)

  if timeout:
    try:
      signal.signal(signal.SIGALRM, alarm_handler)
      signal.alarm(3*60)  # we will timeout after 3 minutes 

      p.wait()
      signal.alarm(0)  # reset the alarm
    except Alarm:
      os.killpg(p.pid, signal.SIGTERM)
      # raise an assertion so we can continue execution after 
      #  (should really have our own exception but fk it)
      raise AssertionError("Timeout "+operation+"ing swift images")
  else:
      p.wait()

  return p



def swift(operation, bucket, *args):
  """operation: upload, download
  bucket: bucket number
  args: files needed to download
  """
  # if the image is migging, upload it
  cache = False
  process = do_swift_command(_to_proxy_url(settings.SWIFT_PROXY1), \
                                 operation, bucket, True, *args)
  if process.returncode != 0:
    message = process.communicate()[1]
    print "Warning: Failed on swift host %s with %s, trying on %s" % \
        (settings.SWIFT_PROXY1, message, settings.SWIFT_PROXY2)
    if operation == "download" and "Object" in message and "not found" in message:
        cache = True


    process = do_swift_command(_to_proxy_url(settings.SWIFT_PROXY2), operation, bucket, True, *args)
  assert process.returncode == 0, "Failed on swift host %s with %s" % \
      (settings.SWIFT_PROXY2, process.communicate()[1])
  if cache:
      print "Uploading the image to local cluster..."
      process = do_swift_command(_to_proxy_url(settings.SWIFT_PROXY1), "upload", bucket, True, *args)
      if process.returncode != 0:
          message = process.communicate()[1]
          print "Uploading failed." + message

if __name__ == '__main__':   
  swift("download", "p233r094", 'p233r094_7dt20040310.SR.b03.tif.gz', 'p233r094_7dt20040310.SR.b04.tif.gz')
