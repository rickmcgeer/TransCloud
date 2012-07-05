from owslib.wms import WebMapService
from owslib.wms import ServiceException
import png
import psycopg2
import math


# these correspond to the selected column num in the SQL statement
GID = 0
CITY_NAME = 1
CV_HULL = 2
XMIN = 3
YMIN = 4
XMAX = 5
YMAX = 6

# database constants
CITY_TABLE = "cities"#"map"#"cities"
GIS_DATABASE = "gisdemo"#"world"#"gisdemo"
DB_USER = "postgres"#"gisdemo"#"postgres"
DB_PASS = ""#"123456"#""

# number of pixels per meter
M_PER_PIXEL = 30

# projection SRID
WSG84 = "4326"
GEOG = WSG84

# Debug stuff
PRINT_IMG = True # print to /tmp/ when True
PRINT_DBG_STR = True # print to stdout

# dict for worldwide wms servers
WMS_SERVER = {'canada':"http://ows.geobase.ca/wms/geobase_en", 'us':None}



def query_database():

    conn = psycopg2.connect(database=GIS_DATABASE, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()

    select = "gid, name, ST_AsText(ST_ConvexHull(ST_Transform(the_geom,"+GEOG+"))),"\
        "ST_XMin(ST_Transform(the_geom,"+GEOG+")), ST_YMin(ST_Transform(the_geom,"+GEOG+\
        ")), ST_XMax(ST_Transform(the_geom,"+GEOG+")), ST_YMax(ST_Transform(the_geom,"+GEOG+"))"

    where = "name LIKE 'VIC%' OR name LIKE 'VAN%' OR name LIKE 'EDM%' OR name LIKE 'CAL%' OR name LIKE 'TOR%'"
    #where = "name LIKE 'HOPE'"

    query = "SELECT " + select + " FROM " + CITY_TABLE + " WHERE " + where + ";"

    cur.execute(query)

    records = cur.fetchall()

    cur.close()
    conn.close()

    return records



def create_update_statement(greenspace, gid):

    return "UPDATE cities SET greenspace=" + str(greenspace) + " WHERE gid=" + str(gid) + ";"



def update_database(query):

    #print "UPDATING DATABSE: ", query

    try:
        conn = psycopg2.connect(database=GIS_DATABASE, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        cur.execute(query)
        # we must commit our transaction
        conn.commit()

        cur.close()
        conn.close()

    except psycopg2.ProgrammingError as e:
        print e



def get_wms_server(bbox):

    # bbox[0] is min x, [1] is min y, [2] max x, [3] max y
    if bbox[0] > -140 and bbox[1] > 42 and bbox[2] < -50 and bbox[3] < 70:
        return WMS_SERVER['canada']

    return None



# The following three functions are from http://python.net/~gherman/convexhull.html 
# by Dinu C. Gherman 
def _myDet(p, q, r): # this is really just the cross prod
    """Calc. determinant of a special matrix with three 2D points.

    The sign, "-" or "+", determines the side, right or left,
    respectivly, on which the point r lies, when measured against
    a directed vector from p to q.
    """

    # We use Sarrus' Rule to calculate the determinant.
    # (could also use the Numeric package...)
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



def _isPointInPolygon(r, P):
    "Is point r inside a given polygon P?"

    # We assume the polygon is a list of points, listed clockwise!
    for i in xrange(len(P[:-1])):
        p, q = P[i], P[i+1]
        if not _isRightTurn((p, q, r)):
            return 0 # Out!        

    return 1 # It's within!



def calc_greenspace(img, box, polygon, gid=0, city=""):

    bytes_of_png = img.read()
    image = png.Reader(bytes=bytes_of_png)

    px_width, px_height, rgbs, metadata = image.read() # image.asRGBA()
    rgbs = list(rgbs)

    # debug, write image /tmp/<gid>-org.png
    if PRINT_IMG:
        fname = "/tmp/" + city + str(gid) 
        wt = png.Writer(width=px_width, height=px_height, alpha=True, bitdepth=8)
        orgf = open(fname+"-org.png", 'wb')
        wt.write(orgf, rgbs)
        orgf.close()

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
                if green[x_pos] > red[x_pos] and green[x_pos] > blue[x_pos]:
                    gs+=1
                
                # debug, make the image white under the polygon
                if PRINT_IMG:
                    rgbs[y_pos][x_pos*4] = rgbs[y_pos][1+x_pos*4] = rgbs[y_pos][2+x_pos*4] = 255

            x_pos+=1
        y_pos+=1

    # debug, write modified image /tmp/<gid>-mod.png
    if PRINT_IMG:
        modf = open(fname+"-mod.png", 'wb')
        wt.write(modf, rgbs)
        modf.close()

    return float(gs) / float(px)



def wkt_to_list(wkt):
    """ convert wkt polygon string to a list of x,y points as floats """

    # get rid of all the brackets and split into a list of strings
    str_point_list = wkt.split('((')[1].split('))')[0]\
        .replace('(', '').replace(')', '')\
        .replace(',', '$').replace(' ', ',').split('$')
    
    # split the list into a list of lists holding coords
    points = [pt_str.split(',') for pt_str in str_point_list]

    # convert each coord into a float
    point_list = [ [float(coord) for coord in pt] for pt in points]
    return point_list



def get_img_size(long_min, lat_min, long_max, lat_max):
    """ Given a bounding box of lat and long coords calculates
    the image size in pixels required to encompass the area """

    conn = psycopg2.connect(database=GIS_DATABASE, user=DB_USER, password=DB_PASS)
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

    # get the width and height of image in pixels
    x_pixels = int(math.ceil(x_meters / M_PER_PIXEL))
    y_pixels = int(math.ceil(y_meters / M_PER_PIXEL))

    cur.close()
    conn.close()

    return (x_pixels, y_pixels)
    


def main():
    records = query_database()

    batch_size = 5 # could make fn of len(records) when that works
    num_updates = 0
    update_stmnt = ""

    wms = WebMapService('http://ows.geobase.ca/wms/geobase_en', version='1.1.1')
#print wms.identification.type
#print wms.identification.version
#print wms.identification.title
    wms.identification.abstract
#print list(wms.contents)
#print wms['imagery:landsat7'].styles

    for record in records:

        # box is floats: [xmin, ymin, xmax, ymax]
        box = record[XMIN:]
        serv = get_wms_server(box)
        if serv:
            #print serv
            #wms = WebMapService(serv, version='1.1.1')
            #wms.identification.abstract

            img_size = get_img_size(box[0], box[1], box[2], box[3])
            coord_sys = "EPSG:" + GEOG
            try:
                img = wms.getmap(layers=['imagery:landsat7'],
                                 styles=[],
                                 srs=coord_sys,
                                 bbox=box,
                                 size=img_size,
                                 format='image/png',
                                 transparent=True
                                 )

                polygon = wkt_to_list(record[CV_HULL])
                #print polygon
                greenspace = calc_greenspace(img, box, polygon, record[GID], record[CITY_NAME])
                update_stmnt += create_update_statement(greenspace, record[GID])
                num_updates+=1

                # batch updates to the database to avoid creating many connections
                if num_updates >= batch_size:
                    update_database(update_stmnt)
                    update_stmnt = ""
                    num_updates = 0

                if PRINT_DBG_STR:
                    print record[GID], record[CITY_NAME], img_size, greenspace

            except ServiceException as e:
                print e
        #else:
            #print record[CITY_NAME], box, "not within our data range!"

    if len(update_stmnt):
        update_database(update_stmnt)


if __name__ == '__main__':
    main()
