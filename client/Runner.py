'''
Created on 2010-03-08

@author: cmatthew Chris Matthews <cmatthew@cs.uvic.ca>
'''

import subprocess
import threading
import time
import fcntl
import os

class RunningProcess(threading.Thread):
    """Runs and monitors a process.
    """
    def __init__(self, command, callbacks ,poll_time=0.1):
        """Create a new running process from this client. 
        @param command: the command to run (as a list of string arguments) eg ['/bin/ls','-eal']
        @param callbacks: pass list of new output lines as they come in to these functions.
        @param poll_time:  time in seconds between output polling (floats okay)  """
        self.output = []
        self.callbacks = callbacks
        threading.Thread.__init__(self)
        self.start_time = time.time()
        self.end_time = 0
        self.poll_time = poll_time
       
        print 'Running: ', str(' '.join(command))
        self.p = subprocess.Popen(command,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE
                )
        
       
     
      
    def _poll_stderr(self):
        while True:
            new_out_items = ""
            try:
              new_out_items = self.p.stderr.readline()
            except: 
              pass
            self._append_output(new_out_items)
            if self.is_dead() or self.is_ended():
              return
            
            time.sleep(self.poll_time)  
      
    def run(self):
        """Thread Start"""
        thread = threading.Thread(target=self._poll_stderr())
        thread.start()
        while True:
            print ".",
            new_out_items = ""
       
            try:
              new_out_items = self.p.stdout.readline()      
            except: 
              pass
            self._append_output(new_out_items)
            
            if self.is_dead():
                self.cleanup()
                print "One of the subprocesses aborted abnormally."
                print "Log: %s\n%s"%(self.out, self.err)
                return self.p.returncode
            if self.is_ended():
                self.cleanup()
                run_time = self.end_time-self.start_time
                print "Subprocess finished in: %d seconds"%(run_time)
                self.run_time = run_time
                return self.p.returncode
            time.sleep(self.poll_time)  
                
    def _append_output(self, new_lines):
      if new_lines == None or len(new_lines) == 0:
        return
      else:
        self.output.append(new_lines)
        for func in self.callbacks:
            func(new_lines)
      
      
    def sync_run(self):
      """Run synchronusly"""
      return self.run()
    
    def wait(self):
        """wrapper of process.wait()"""
        rc = self.p.wait()
        return rc
    
    def is_dead(self):
        """True if the process returned with a non-zero code."""
        if (self.p.poll() != None):
            if (self.p.returncode != 0):
                return True
        return False
    
    def is_ended(self):
        """True if the process is ended and has a good return code."""
        if (self.p.poll() != None):
            if (self.p.returncode == 0):
                return True
        return False
    
    def poll(self):
        """wrapper of process.poll() -- get the state of the process, return return code or None if still going"""
        return self.p.poll()

    def get_return_code(self):
        """wrapper of process.returncode"""
        return self.p.returncode
    
    def get_err_log(self):
            return self.err
    
    def get_out_log(self):
            self._append_output(self.out)
            
            return self.output
    
    def get_pid(self):
        return self.p.pid
    
    def cleanup(self):
        """Collect all the logs etc and results"""
        (self.out, self.err) = self.p.communicate()
        if self.out != None:
          self.output.append(self.out)

        self.end_time = time.time()
        
        
    def __del__(self):
        self.output = None
   
        del(self.p)
        self.p = None
        self.output = None
        self.err = None
        

def print_results(new_items):
  print new_items,

def send_to_server(new_items):
  print ">>>>", new_items,
  #TODO this is where you regx the output to get data

if __name__ == '__main__':
    r = RunningProcess(['/bin/ping','-c', '10', 'localhost'], [print_results, send_to_server])
    r.start()
    r.wait() # don't have to do this
    print r.get_out_log()
    