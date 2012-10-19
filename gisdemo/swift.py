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

def swift(operation, bucket, *args):
  """operation: upload, download
  bucket: bucket number
  args: files needed to download
  """
  command = "swift -A "+settings.SWIFT_PROXY+" -U "+settings.SWIFT_USER+ \
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

  assert p.returncode == 0, "Failed with %s"%(p.communicate()[1])

if __name__ == '__main__':   
  swift("download", "p233r094", 'p233r094_7dt20040310.SR.b03.tif.gz', 'p233r094_7dt20040310.SR.b04.tif.gz')
