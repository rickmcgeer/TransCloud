from owslib.wms import WebMapService
from owslib.wms import ServiceException
import png
import psycopg2
import math
import datetime
import sys


# CRITICAL TODO's:
#
#  - Make initial query pull only correct data, we must modify either 
#      the table or where clause in query_database()
#     After that we must make get_wms_server() behave better as it checks
#      if around canada right now
#


# these correspond to the selected column num in the SQL statement
GID = 0
CITY_NAME = 1
CV_HULL = 2
XMIN = 3
YMIN = 4
XMAX = 5
YMAX = 6


# val of all pixels we want the space around the polygon to be
MASK_COLOUR = 0

LOW_GREEN_VAL = 0.0001

# database constants
DB_USER = "postgres"#"gisdemo"#"postgres"
DB_PASS = ""#"123456"#""
GIS_DATABASE = "world"#"gisdemo"
PY2PG_TIMESTAMP_FORMAT = "YYYY-MM-DD HH24:MI:SS:MS"

CITY_TABLE = {'canada':"ca_cities", 'us':"us_cities", 'all':"map"}
ID_COL = "gid"
NAME_COL = "name"
GEOM_COL = "the_geom"
GREEN_COL = "greenspace"

IMG_TABLE = "processed"
IMG_NAME_COL = "file_path"
START_T_COL = "process_start_time"
END_T_COL = "process_end_time"
SERV_NAME_COL = "server_name"


# number of pixels per meter
M_PER_PIXEL = 30

# projection SRID
WSG84 = "4326"
GEOG = WSG84

# do we, and if so where do we want to print images
PRINT_IMG = True
IMG_LOC = "/tmp/"

PRINT_DBG_STR = True # print to stdout

# dict for worldwide wms servers
WMS_SERVER = {'canada':"http://ows.geobase.ca/wms/geobase_en", 'us':None}
WMS_LAYER = {'canada':['imagery:landsat7'], 'us':[]}

# 
LOG_FILE = None
LOG_NAME = "getmap.log"



def log(*args):
    """ Write a timestamp and the args passed to the log. 
    If there is no log file we treat stderr as our log
    """
    
    if LOG_FILE:
        lf = LOG_FILE
    else:
        lf = sys.stderr

    msg = str(datetime.datetime.now()) + ": "
    for arg in args:
        msg += str(arg) + " "
    lf.write(msg+'\n')



def query_database(region):
    """ Selects data from the database, and returns a list of records. 
    If an error occurs connecting to the database, or executing the 
    query, we simply return an empty list.
    """
	
    #records = []
    try:
        conn = psycopg2.connect(database=GIS_DATABASE,
                                user=DB_USER,
                                password=DB_PASS)
        cur = conn.cursor()
        #print "con=", conn, "cur=", cur	

        select = ID_COL+", "+NAME_COL+", "\
            "ST_AsText(ST_ConvexHull(ST_Transform("+GEOM_COL+","+GEOG+"))),"\
            "ST_XMin(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_YMin(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_XMax(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_YMax(ST_Transform("+GEOM_COL+","+GEOG+"))"

        # keep WHERE in here incase we dont want a where clause
        #where = " WHERE name LIKE 'VIC%' OR name LIKE 'VAN%' OR name LIKE 'EDM%'"
        #where = " WHERE name LIKE 'HOPE'"
        where = " WHERE "+GREEN_COL+"=0"
		
        #limit = " LIMIT 50"
        limit = ""

        query = "SELECT " + select + " FROM " + CITY_TABLE[region] + where + limit + ";"

        cur.execute(query)

        records = cur.fetchall()
        print len(records)

        cur.close()
        conn.close()
		
        return records

    except psycopg2.ProgrammingError as e:
        log("Failed to fetch from database:", e)
        return []

    # we always want to return a list
    #finally:
    #    return records



def create_update_statement(greenspace, gid, name, start, end, serv_name, location):
    """ Returns an sql update statement as a string which sets
    the record with the matching gid's greenspace value, image 
    name, and timestamps
    """

    if name is None:
        name = ""

    # format the python timestamps into something postgres can understand
    st_time = "to_timestamp('"+str(start)+"', '"+PY2PG_TIMESTAMP_FORMAT+"')"
    end_time = "to_timestamp('"+str(start)+"', '"+PY2PG_TIMESTAMP_FORMAT+"')"

    green_tbl = "UPDATE "+CITY_TABLE[location]\
        +" SET "+GREEN_COL+"=" + str(greenspace)\
        + " WHERE "+ID_COL+"=" + str(gid) + ";"

    image_tbl = "UPDATE "+IMG_TABLE\
        +" SET "+IMG_NAME_COL+"='" + name + str(gid) + "-mod.png', "\
        +START_T_COL+"="+st_time+", "\
        +END_T_COL+"="+end_time+", "\
        +SERV_NAME_COL+"='"+serv_name+"'"\
        +" WHERE "+ID_COL+"=" + str(gid) + ";"

    return green_tbl + image_tbl



def update_database(query):
    """ Given a string continging sql, will connect to the
    database and perform the sql query, if the query fails 
    for any reason we log the error but continue execution.
    """

    #print query
    try:
        conn = psycopg2.connect(database=GIS_DATABASE,
                                user=DB_USER,
                                password=DB_PASS)
        cur = conn.cursor()
        cur.execute(query)

        # we must commit our transaction
        conn.commit()

        cur.close()
        conn.close()

    except psycopg2.ProgrammingError as e:
        log("Failed to update database:", e)



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



def write_image(fname, w, h, pixels):
    """ Writes a png image to the filesystem """

    try:
        wt = png.Writer(width=w, height=h, alpha=True, bitdepth=8)
        f = open(IMG_LOC+fname, 'wb')
        wt.write(f, pixels)
        f.close()
    except IOError as e:
        log(e)



def calc_greenspace(img, box, polygon, gid, city):
    """ given a png image, bounding box, and polygon will count the 
    percentage of greenspace contained in the image within the polygon
    """
	
    if not city:
        city = ""

    bytes_of_png = img.read()
    image = png.Reader(bytes=bytes_of_png)

    # extract image data
    px_width, px_height, rgbs, metadata = image.read()
    # we get lists of arrays of pixels, one list ele to a row
    rgbs = list(rgbs) 

    # write original image
#    if PRINT_IMG:
#        write_image(city+str(gid)+"-org.png",
#                    px_width, px_height, rgbs)

    # for placing the pixels in the coord system
    min_x = box[0]
    max_y = box[3]
    # increment = length x|y / width|height
    x_incr = (box[2] - box[0]) / px_width
    y_incr = (box[3] - box[1]) / px_height
    
    gs = 0
    px = 0
    y_pos = 0
    while y_pos < px_height:

        red = rgbs[y_pos][0::4]
        green = rgbs[y_pos][1::4]
        blue = rgbs[y_pos][2::4]

        x_pos = 0
        while x_pos < px_width:
            # place pixel in bounding box
            px_x = min_x + (x_pos * x_incr)
            px_y = max_y - (y_pos * y_incr)
        
            if _isPointInPolygon([px_x, px_y], polygon):
                px+=1
                # if green is the most promemant colour, we count as greenspace
                if green[x_pos] > red[x_pos] and green[x_pos] > blue[x_pos]:
                    gs+=1
                
            # change pixels not in the polygon
            elif PRINT_IMG:
                #rgbs[y_pos][x_pos*4] = rgbs[y_pos][1+x_pos*4] = rgbs[y_pos][2+x_pos*4] = MASK_COLOUR
                rgbs[y_pos][3+x_pos*4] = MASK_COLOUR

            x_pos+=1
        y_pos+=1

    # write modified image
    if PRINT_IMG:
        write_image(city+str(gid)+"-mod.png",
                    px_width, px_height, rgbs)

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

    conn = psycopg2.connect(database=GIS_DATABASE,
                            user=DB_USER,
                            password=DB_PASS)
    cur = conn.cursor()

    def get_dist_from_pts(a, b):
        """ Queries the database to ge the distance in m between 
        2 lat long points """
        
        a_wkt = "POINT(" + str(a[0]) + " " + str(a[1]) + ")"
        b_wkt = "POINT(" + str(b[0]) + " " + str(b[1]) + ")"
 
        query = "SELECT ST_Distance(ST_GeogFromText('SRID="\
            +GEOG+";"+a_wkt+"'),ST_GeogFromText('SRID="+GEOG+";"+b_wkt+"'));"
        cur.execute(query)
        records = cur.fetchall()

        return float(records[0][0])

    # get the x and y length of our bounding box in meters
    x_meters = get_dist_from_pts((long_min, lat_min), (long_max, lat_min))
    y_meters = get_dist_from_pts((long_min, lat_min), (long_min, lat_max))

    if PRINT_DBG_STR:
        print "width:", x_meters, " height:", y_meters
		
    if x_meters < M_PER_PIXEL or y_meters < M_PER_PIXEL:
        return (0,0)

    # get the width and height of image in pixels
    x_pixels = int(math.ceil(x_meters / M_PER_PIXEL))
    y_pixels = int(math.ceil(y_meters / M_PER_PIXEL))

    cur.close()
    conn.close()

    return (x_pixels, y_pixels)
    


def get_wms_server(loc):

    # bbox[0] is min x, [1] is min y, [2] max x, [3] max y
    #if bbox[0] > -140 and bbox[1] > 42 and bbox[2] < -50 and bbox[3] < 70:
    return WMS_SERVER[loc], WMS_LAYER[loc]




def main():

    batch_size = 1 # could make fn of len(records) when that works
    num_updates = 0
    update_stmnt = ""

    location = 'canada'

    records = query_database(location)
	
    #print len(records)

    for record in records:
	
        if record[GID] is None:	
            log("Null GID")
            continue
				
        try:
            # box is floats: [xmin, ymin, xmax, ymax]
            box = record[XMIN:]
            wms_serv, layer = get_wms_server(location)
            if wms_serv:

                start_t = datetime.datetime.now()
                
                wms = WebMapService(wms_serv, version='1.1.1')
                wms.identification.abstract

                img_size = get_img_size(box[0], box[1], box[2], box[3])
                coord_sys = "EPSG:" + GEOG
				
				# must check if the image size is valid
                if img_size[0] and img_size[1]:

                     img = wms.getmap(layers=layer,
                                 styles=[],
                                 srs=coord_sys,
                                 bbox=box,
                                 size=img_size,
                                 format='image/png',
                                 transparent=True
                                 )

                     # get polygon as list of points (ie, not a string)
                     polygon = wkt_to_list(record[CV_HULL])
                
                     # do greenspace calc on image
                     greenspace = calc_greenspace(img, box, polygon, record[GID], record[CITY_NAME])
					 
			    # we should not insert something into the database if the image 
				# is invalid as there is nothing for ricks stuff to read
                else:
                    greenspace = 0
				
                if greenspace:
				
                    end_t = datetime.datetime.now()

                    # append update statement to string
                    update_stmnt += create_update_statement(greenspace,
                                                        record[GID],
                                                        record[CITY_NAME],
                                                        start_t,
                                                        end_t,
                                                        wms_serv,
                                                        location)
                    num_updates+=1

                    # batch updates to the database to avoid creating many connections
                    if num_updates >= batch_size:
                        update_database(update_stmnt)
                        update_stmnt = ""
                        num_updates = 0

                if PRINT_DBG_STR:
                    print record[GID], record[CITY_NAME], img_size, greenspace
                log(record[GID], record[CITY_NAME], img_size, greenspace)

            #else:
                #print record[CITY_NAME], box, "not within our data range!"

        # catch all the errors and send to the log... is this a good idea???
        except Exception as e:
            log("Unexpected exception, process failed:", e)
            raise

    if len(update_stmnt):
        update_database(update_stmnt)
		
    return len(records)


if __name__ == '__main__':

    try:
        LOG_FILE = open(LOG_NAME, 'a')
    except IOError as e:
        print "Failed to open Log:", e, "\nLogging to stderr"

    log("Started")
    proc = main()
    while(proc):
        proc = main()
    log("Stopped")

    if LOG_FILE:
        LOG_FILE.close()
