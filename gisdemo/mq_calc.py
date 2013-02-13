import sys
import os
import greenspace
import json
import optparse
import settings
import tempfile

sys.path.insert(0, './mq/')

import taskmanager


# def mapper(entry, params):
#     #try:
#         import os, json, tempfile, traceback
#         settings.TEMP_FILE_DIR = tempfile.mkdtemp(prefix='mapJob', dir=settings.MACHINE_TMP_DIR)
#         os.chdir(settings.TEMP_FILE_DIR)
#         greencitieslog.start()
#         try:
#             id, name, poly, bb1, bb2, bb3, bb4 = json.loads(entry)   
#         except Exception as e:
#             print "JSON failed", entry
# 	    return [("JSON failure",entry)]
#         try:
#             greenspace.process_city(id,name,poly,(bb1,bb2,bb3,bb4),"all")
#         except Exception as e:
#             msg = "Failed with:", str(e) + "at:\n" + str(traceback.format_exc())
#             greencitieslog.log(msg)
# 	    return [("Failure",msg)]
#         finally:
#             greencitieslog.close()
#         print name, id, "processed."
#         return [("Success",str(id) + " " + name)]


 # def mapper_init(x,y):
 #    print "Mapper Init"
 #    greenspace.init()
 #    print "Mapper Init Done"


if __name__ == '__main__':

    # get command line options
    parser = optparse.OptionParser()
    parser.add_option("-c", "--num_cities", dest="num_cities", type="int", default=5, help="number of cities to run the calculation on")
    (options, args_not_used) = parser.parse_args()

    print "Running with "+str(options.num_cities)+" cities"
    here = os.path.dirname(os.path.realpath(__file__))+"/"
    greenspace.init()
    cities = greenspace.get_cities(1, options.num_cities)

    jobs = []
    manager = taskmanager.TaskManager()
    manager.clear(1)
    for i,c in enumerate(cities):
         job = json.dumps(c ,separators=(',',':'))
         manager.add_task({'task':'greencities','data':job},1)




    


