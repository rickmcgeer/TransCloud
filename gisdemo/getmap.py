from owslib.wms import WebMapService
from owslib.wms import ServiceException
import png
import psycopg2

# these correspond to the selected column num in the SQL statement
GID = 0
CITY_NAME = 1
CV_HULL = 2
XMIN = 3
YMIN = 4
XMAX = 5
YMAX = 6

def query_database():
    conn = psycopg2.connect(database="gisdemo", user="postgres", password="")
    cur = conn.cursor()

    cur.execute("SELECT gid, name, ST_AsText(ST_ConvexHull(the_geom)), ST_XMin(the_geom), ST_YMin(the_geom), ST_XMax(the_geom), ST_YMax(the_geom) FROM cities where name LIKE 'V%';")

    records = cur.fetchall()

#for record in records:
#    print record

    cur.close()
    conn.close()

    return records


def insert_into_database(greenspace, gid):

    sql = "UPDATE cities SET greenspace=" + greenspace + "WHERE gid=" + gid + ";"

    conn = psycopg2.connect(database="gisdemo", user="postgres", password="")
    cur = conn.cursor()

    cur.execute(sql)

    cur.close()
    conn.close()



def get_wms_server(bbox):

    # bbox[0] is min x, [1] is min y, [2] max x, [3] max y
    if bbox[0] < -140 or bbox[1] < 42 or bbox[2] > -50 or bbox[3] > 70:
        return 0
    return 1

# --------------------
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

    assert p != q and q != r and p != r
            
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
# ------------------

def calc_greenspace(img, box, polygon):

    bytes_of_png = img.read()
    image = png.Reader(bytes=bytes_of_png)

    # for placing the pixels in the coord system
    min_x = box[0]
    min_y = box[1]
    len_x = box[2] - box[0]
    len_y = box[3] - box[1]
    
    #print min_x, min_y, len_x, len_y

    rgbs = list(image.asRGBA()[2])
    pixels = 0
    rs = 0
    bs = 0
    gs = 0
    for row in rgbs:
        for pixel in row[0::4]:
            pixels += 1
            if pixel > 128:
                rs += 1
        for pixel in row[1::4]:
            pixels += 1
            if pixel > 128:
                gs += 1
        for pixel in row[2::4]:
            pixels += 1
            if pixel > 128:
                bs += 1


    return pixels, rs, bs, gs


def wkt_to_list(wkt):
    # get rid of all the brackets and split into a list of strings
    str_point_list = wkt.split('((')[1].split('))')[0]\
        .replace('(', '').replace(')', '')\
        .replace(',', '$').replace(' ', ',').split('$')
    
    # split the list into a list of lists holding coords
    points = [pt_str.split(',') for pt_str in str_point_list]

    # convert each coord into a float
    point_list = [ [float(coord) for coord in pt] for pt in points]
    return point_list


def main():
    records = query_database()

    wms = WebMapService('http://ows.geobase.ca/wms/geobase_en', version='1.1.1')
#print wms.identification.type
#print wms.identification.version
#print wms.identification.title
    wms.identification.abstract
#print list(wms.contents)
#print wms['imagery:landsat7'].styles

    for record in records:
    #box = (-123.57411,48.3106147, -123.20006,48.6980295)
        box = record[XMIN:]
        #print box
        serv = get_wms_server(box)
        if serv:
            try:
                img = wms.getmap(layers=['imagery:landsat7'],
                                 styles=[],
                                 srs='EPSG:4326',
                                 bbox=box,
                                 size=(300, 250),
                                 format='image/png',
                                 transparent=True
                                 )
                polygon = wkt_to_list(record[CV_HULL])
                #print polygon
                print record[CITY_NAME], calc_greenspace(img, box, polygon)
            except ServiceException as e:
                print e
        
        #print record[CITY_NAME], box, "not within our data range!"


if __name__ == '__main__':
    main()
