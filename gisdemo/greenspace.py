#from owslib.wms import WebMapService
#from owslib.wms import ServiceException
#import png
#import psycopg2
import math
import datetime

import os
import socket
import settings

from greencitieslog import log
import greencitieslog
import landsatImg
import dbObj
import json
import taskmanager

# NOTE: these should really be in dbObj.py but ahm lay z
# these correspond to the selected column num in the SQL statement
GID = 0
CITY_NAME = 1
CV_HULL = 2
XMIN = 3
YMIN = 4
XMAX = 5
YMAX = 6

servname = "unknown"

pgConn = None

# val of alpha pixels we want the space around the polygon to be
MASK_COLOUR = 0

LOW_GREEN_VAL = 0.0001

# number of pixels per meter aka resolution
M_PER_PIXEL = 30

# do we want to print images
PRINT_IMG = True



# The following is from http://python.net/~gherman/convexhull.html 
# by Dinu C. Gherman 
def _isPointInPolygon(r, P):
    "Is point r inside a given polygon P?"

    def _myDet(p, q, r): # this is really just the cross prod
        """Calc. determinant of a special matrix with three 2D points.

        The sign, "-" or "+", determines the side, right or left,
        respectivly, on which the point r lies, when measured against
        a directed vector from p to q.
        """

        # We use Sarrus' Rule to calculate the determinant.
        sum1 = q[0]*r[1] + p[0]*q[1] + r[0]*p[1]
        sum2 = q[0]*p[1] + r[0]*q[1] + p[0]*r[1]

        return sum1 - sum2

    def _isRightTurn((p, q, r)):
        "Do the vectors pq:qr form a right turn, or not?"

        # this is not a valid assertion for us, 
        #  as some points may be directly on the polygon
        #assert p != q and q != r and p != r

        if _myDet(p, q, r) < 0:
            return 1
        else:
            return 0

    # We assume the polygon is a list of points, listed clockwise!
    for i in xrange(len(P[:-1])):
        p, q = P[i], P[i+1]
        if not _isRightTurn((p, q, r)):
            return 0 # Out!        

    return 1 # It's within!



def calc_greenspace(img, polygon):
    """ given a png image, bounding box, and polygon will count the 
    percentage of greenspace contained in the image within the polygon
    """

    # for placing the pixels in the coord system
    min_x = img.bbox.xmin
    max_y = img.bbox.ymax
    # x and y increase per pixel
    x_incr = img.getXPerPixel()
    y_incr = img.getYPerPixel()
    
    px_width = img.px_w
    px_height = img.px_h

    gs = 0
    px = 0
    y_pos = 0
    while y_pos < px_height:

        red = img.rgbs[y_pos][0::4]
        green = img.rgbs[y_pos][1::4]
        blue = img.rgbs[y_pos][2::4]
        alpha = img.rgbs[y_pos][3::4]

        x_pos = 0
        while x_pos < px_width:
            r = red[x_pos]
            g = green[x_pos]
            b = blue[x_pos]
            a = alpha[x_pos]

            # place pixel in bounding box
            px_x = min_x + (x_pos * x_incr)
            px_y = max_y - (y_pos * y_incr)
               # if we are transparent dont count us!
            if not (a == MASK_COLOUR):
                if _isPointInPolygon([px_x, px_y], polygon):
                    px+=1
                    # if green is the most promemant colour, we count as greenspace
                    if g > r and g > b:
                        gs+=1

                # Change pixels not in the polygon
                else:
                    img.rgbs[y_pos][3+x_pos*4] = MASK_COLOUR

            x_pos+=1
        y_pos+=1

    # write modified image
    img.writeImg()
    
    if float(px) == 0:
        return 0

    # return num of greenspace pixels / pixels in polygon
    return float(gs) / float(px)



def wkt_to_list(wkt):
    """ convert wkt polygon string to a list of x,y points as floats """

    # get rid of all the brackets and split into a list of strings
    str_point_list = wkt.split('((')[1].split('))')[0]\
        .replace('(', '').replace(')', '')\
        .replace(',', '$').replace(' ', ',').split('$')
    
    # split the list into a list of lists holding coords
    points = [pt_str.split(',') for pt_str in str_point_list]

    # convert each point into a pair of floats
    point_list = [ [float(coord) for coord in pt] for pt in points]
    return point_list



def get_img_size(long_min, lat_min, long_max, lat_max):
    """ Given a bounding box of lat and long coords calculates
    the image size in pixels required to encompass the area """

    assert pgConn, "get_img_size(): Must have a Postgres connection!"

    def get_dist_from_pts(a, b):
        """ Queries the database to ge the distance in m between 
        2 lat long points """
        
        query = pgConn.createCoordQuery(a, b)
        records = pgConn.performSelect(query)

        return float(records[0][0])

    # get the x and y length of our bounding box in meters
    x_meters = get_dist_from_pts((long_min, lat_min), (long_max, lat_min))
    y_meters = get_dist_from_pts((long_min, lat_min), (long_min, lat_max))

    if settings.PRINT_DBG_STR:
        print "width:", x_meters, " height:", y_meters
		
    if x_meters < M_PER_PIXEL or y_meters < M_PER_PIXEL:
        return (0,0)

    # get the width and height of image in pixels
    x_pixels = int(math.ceil(x_meters / M_PER_PIXEL))
    y_pixels = int(math.ceil(y_meters / M_PER_PIXEL))

    return (x_pixels, y_pixels)


def process_city(gid, cityname, convex_hull, xmin_box, location, testing=False):

    assert (gid is not None and convex_hull is not None), "Process city inputs are None"
    if cityname == None:
        cityname = "No Name with ID:" + str(gid)
    greencitieslog.prefix = cityname
    # box is floats: [xmin, ymin, xmax, ymax]
    box = xmin_box
    #img_w, img_h = get_img_size(pgConn, box[0], box[1], box[2], box[3])
    #print " -> w:h = ", img_w, ":", img_h

    greenspace = 0
    #if img_w and img_h:

    coord_sys = "EPSG:" + dbObj.GEOG

    start_t = datetime.datetime.now()
    imgname = "missing"
    greenspace = 0.0
    servername = socket.gethostname()
    if not testing:
        lsimg = landsatImg.GrassLandsat(gid, cityname, box, coord_sys, location)

        log("Getting Image List")
        lsimg.getImgList(pgConn)

        log("Getting Images from Swift")
        lsimg.getSwiftImgs()

        log("Combine into PNG")
        lsimg.combineIntoPng()

        log("Read Image Data")
        lsimg.img.readImgData()

        # get polygon as list of points (ie, not a string)
        log("Extracting Polygon points")
        polygon = wkt_to_list(convex_hull)

        log("Calculating Greenspace")
        greenspace = calc_greenspace(lsimg.img, polygon)

        log("Greenvalue of " ,str(greenspace), " was found")
        
        log("RESULT:",gid, cityname, greenspace)
    # pgConn.createUpdateStmnt(greenspace,
    #                                             lsimg.gid, lsimg.city,
    #                                             start_t, end_t,
    #                                             lsimg.img.imgname,
    #                                             servname, location)
        lsimg.uploadToSwift()
        imgname = lsimg.img.imgname
        # only in for test
        tmp_directory = lsimg.file_manager.tmp_file_dir
        del lsimg
        if os.path.exists(tmp_directory):
            print 'Cleanup failed to delete ' + tmp_directory
    else:
        print "warning testing mode"
        
        
    end_t = datetime.datetime.now()
    result_dict = {'id':gid,
                   'name':cityname,
                   'greenspace_val':greenspace,
                   'stime':start_t.isoformat(),
                   'etime':end_t.isoformat(),
                   'imgname':imgname,
                   'servername':servername,
                   'location':location
                   }
    return result_dict

def get_cities(location, num_cities=10):
    
    log("Getting new cities from database")
    select_query = pgConn.createSelectQuery(location, num_cities)
    records = pgConn.performSelect(select_query)
    log("Fetched", len(records), location, "records")
    return records


def main(location):
    global pgConn
    records = get_cities(location)
    os.chdir(settings.TEMP_FILE_DIR)
    for record in records:
        try:
            log("Processing", record[GID], record[CITY_NAME])
            
            if record[GID] is None:	
                log("Null GID, skipping")
                continue
            
            process_city(record[GID], record[CITY_NAME], record[CV_HULL], record[XMIN:], location)

        except AssertionError as e:
            log(e)
        #except Exception as e:
        #    log("Processing ", record[CITY_NAME], " with error ", str(e))

    del pgConn
    return len(records)

def process_city_from_json(json_string, testing=False):
    id, name, poly, bb1, bb2, bb3, bb4 = json.loads(json_string)   
    location = taskmanager.get_local_site_name()
    green_results = process_city(id, name, poly, (bb1, bb2, bb3, bb4), location, testing=testing)
    return green_results


def init():
    global pgConn
    servname = socket.gethostname()

    greencitieslog.start()
    
    log("Starting Green Cities on", servname)
    log("Connecting to database")
    pgConn = dbObj.pgConnection()

def close():
    greencitieslog.close()

    


def test_greencity():

    init()

    bolshaya = '[9554,"BOL\'SHAYA KAZINKA","POLYGON((40.0881958007812 50.2370834350586,40.0603332519531 50.2511100769043,40.0602493286133 50.2524719238281,40.1050834655762 50.2676658630371,40.1071929931641 50.2677230834961,40.1189460754395 50.2620277404785,40.119026184082 50.2601928710938,40.0881958007812 50.2370834350586))",40.0602493286133,50.2370834350586,40.119026184082,50.2677230834961]'

    gdict = process_city_from_json(bolshaya)
    
    assert gdict['greenspace_val'] ==  0.68678949431595449, "Did did not get correct greenspace Bolshaya. got:%s"%(str(gdict))

# def test_noname():

#     init()
    
#     no_name = '[21827,null,"POLYGON((-102.181838989258 31.132007598877,-102.1\
# 90315246582 31.1407642364502,-102.190841674805 31.1421413421631,-102.18815612793 31.1444206237793,-102.180686950684 31.144380569458,-102.175392150879 31.1393089294434,-102.17539\
# 2150879 31.138391494751,-102.181838989258 31.132007598877))",-102.190841674805,31.132007598877,-102.175392150879,31.1444206237793]'

#     gdict = process_city_from_json(no_name)

#     assert gdict['greenspace_val'] !=  0.0, "Did did not get correct greenspace for No Name. got:%s"%(str(gdict))

# def test_LA():
#     init()

#     LA = '[19804,"LOS ANGELES","POLYGON((-117.864311218262 33.5829620361328,-117.925109863281 33.6035270690918,-118.392883300781 33.7773933410645,-118.396179199219 33.7792167663574,-118.670768737793 34.1548309326172,-118.673080444336 34.1644477844238,-118.673683166504 34.1699485778809,-118.661354064941 34.2002944946289,-118.645034790039 34.224250793457,-118.615776062012 34.2666091918945,-118.611419677734 34.2712249755859,-118.607582092285 34.2735366821289,-118.554397583008 34.3013458251953,-118.476356506348 34.3297004699707,-118.467552185059 34.3315734863281,-118.462593078613 34.3325119018555,-118.459846496582 34.3329849243164,-118.42456817627 34.3349647521973,-118.41739654541 34.3349952697754,-118.409111022949 34.3327369689941,-118.407455444336 34.3322830200195,-117.848747253418 34.1541290283203,-117.833892822266 34.1473617553711,-117.823989868164 34.1423110961914,-117.818542480469 34.1297798156738,-117.749877929688 33.8711585998535,-117.749877929688 33.8656539916992,-117.751007080078 33.8046684265137,-117.753219604492 33.7757797241211,-117.770217895508 33.6969375610352,-117.770767211914 33.6960220336914,-117.77897644043 33.682731628418,-117.864311218262 33.5829620361328))",-118.673683166504,33.5829620361328,-117.749877929688,34.3349952697754]'

#     gdict = process_city_from_json(LA)

#     assert gdict['greenspace_val'] <  0.9, "Did did not get correct greenspace for LA. got:%s"%(str(gdict))


if __name__ == '__main__':
    init()
    main(1)

