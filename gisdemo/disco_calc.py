from disco.core import Job, result_iterator
from disco.worker.classic.worker import Worker
import disco.worker.classic.func
import disco
import sys
import os
import greenspace
import tempfile
import json
import SimpleHTTPServer
import SocketServer
import threading
import optparse
import settings
import tempfile



def mapper(entry, params):
    #try:
        import os, json, tempfile, traceback
        settings.TEMP_FILE_DIR = tempfile.mkdtemp(prefix='mapJob', dir=settings.MACHINE_TMP_DIR)
        os.chdir(settings.TEMP_FILE_DIR)
        greencitieslog.start()
        try:
            id, name, poly, bb1, bb2, bb3, bb4 = json.loads(entry)   
        except Exception as e:
            print "JSON failed", entry
	    return [("JSON failure",entry)]
        try:
            greenspace.process_city(id,name,poly,(bb1,bb2,bb3,bb4),"all")
        except Exception as e:
            msg = "Failed with:", str(e) + "at:\n" + str(traceback.format_exc())
            greencitieslog.log(msg)
	    return [("Failure",msg)]
        finally:
            greencitieslog.close()
        print name, id, "processed."
        return [("Success",str(id) + " " + name)]


def mapper_init(x,y):
    print "Mapper Init"
    greenspace.init()
    print "Mapper Init Done"


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-c", "--num_cities", dest="num_cities", type="int", default=2, help="number of cities to run the calculation on")
    parser.add_option("-m", "--num_mappers", dest="num_mappers", type="int", default=4, help="number of nodes to map the job to")
    (options, args_not_used) = parser.parse_args()
    print "Running with "+str(options.num_cities)+" cities and "+str(options.num_mappers)+" mappers"
    here = os.path.dirname(os.path.realpath(__file__))+"/"
    greenspace.init()
    cities = greenspace.get_cities(1, options.num_cities)
    input_files = []
    fds = []
    for n in xrange(options.num_mappers):
        fid,name = tempfile.mkstemp(dir=".")
        print "Temp data file", fid, name
        f = os.fdopen(fid, "w+b")
        fds.append(f)
        input_files.append(name)

    for i,c in enumerate(cities):
        fd = fds[i%len(input_files)]
        json.dump(c,fd ,separators=(',',':'))
        fd.write("\n")
        print "City", c[1], "to",fd 
    for f in fds:
        f.close()

    PORT = 8081
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    print "serving at port", PORT
    def start_server():
	httpd.serve_forever()
    threading.Thread(target=start_server).start()
    input_files = ["http://node0:" + str(PORT) + "/" + os.path.basename(name) for name in input_files]
    print input_files

    print "Setting up Disco"
    src_files = ["settings.py",
                  "greenspace.py",
                  "landsatImg.py",
                  "greencitieslog.py",
                  "partition.py",
                  "trim.py",
                  "dbObj.py",
                  "combine.py",
                  "gcswift.py"
                  ]
    target_dir = here
            
    

    rest = [(x[:-3],here+x) for x in src_files]

    for x in rest:
        print "import ",x[0]
    print "Making Job"        
    print input_files
    worker = Worker(required_modules=rest,
                    master='http://disco1:8989',
                    input=input_files, 
                    map=mapper,  
                    map_init=mapper_init,
		    sort=False,
		    reduce=disco.worker.classic.func.nop_reduce)
    job = Job(name="GreenSpace",worker=worker)
    
    print "Running Job"
    job.run()
    try:
	    print "Job run"
	    r = job.wait(show=True)
	    print "Done Job"
    finally:
	    httpd.shutdown()

    for status, reason in result_iterator(r):
        print status, reason


