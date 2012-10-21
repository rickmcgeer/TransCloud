#from owslib.wms import WebMapService
#from owslib.wms import ServiceException
#import png
#import psycopg2
import math
import datetime

import os
import socket
import settings

from logging import log
import logging
import landsatImg
import dbObj




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

# number of pixels per meter
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


def process_city(gid, cityname, convex_hull, xmin_box, location):

    assert (gid is not None and cityname is not None and convex_hull is not None), "Process city inputs are None"
    logging.prefix = cityname
    # box is floats: [xmin, ymin, xmax, ymax]
    box = xmin_box
    #img_w, img_h = get_img_size(pgConn, box[0], box[1], box[2], box[3])
    #print " -> w:h = ", img_w, ":", img_h

    greenspace = 0
    #if img_w and img_h:

    coord_sys = "EPSG:" + dbObj.GEOG

    start_t = datetime.datetime.now()

    log("Invoking Grass")
    lsimg = landsatImg.grasslandsat(gid, cityname, box, coord_sys, location)

    log("Getting Image List")
    lsimg.getImgList(pgConn)

    lsimg.checkImages()



def main(location):
	
    global pgConn
    log("Connecting to database")
    pgConn = dbObj.pgConnection()

    log("Getting new cities from database")
    select_query = pgConn.createSelectQuery(location)
    records = pgConn.performSelect(select_query)
    log("Fetched", len(records), location, "records")

    for record in records:
        try:
            log("Processing", record[GID], record[CITY_NAME])

            if record[GID] is None:	
                log("Null GID, skipping")
                continue
            
            process_city(record[GID], record[CITY_NAME], record[CV_HULL], record[XMIN:], location)

        except AssertionError as e:
            log(e)
        except Exception as e:
            log("Proccsing", record[CITY_NAME], "with error", str(e))

    del pgConn
    return len(records)



if __name__ == '__main__':

    servname = socket.gethostname()

    logging.start()
    
    log("Starting Green Cities on", servname)
    
    os.chdir(settings.TEMP_FILE_DIR)

    try:
        proc = main('all')
    finally:
        logging.close()
