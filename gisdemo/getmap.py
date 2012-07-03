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

    cur.execute("SELECT gid, name, ST_AsText(ST_ConvexHull(the_geom)), ST_XMin(the_geom), ST_YMin(the_geom), ST_XMax(the_geom), ST_YMax(the_geom) FROM cities WHERE name LIKE 'VICTORIA';")

    records = cur.fetchall()

#for record in records:
#    print record

    cur.close()
    conn.close()

    return records


def get_wms_server(bbox):
    if bbox[0] > -50 or bbox[1] < 42 or bbox[2] < -140 or bbox[3] > 70:
        return 0
    return 1

def calc_greenspace(img):

    bytes_of_png = img.read()
    image = png.Reader(bytes=bytes_of_png)

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


    print pixels, rs, bs, gs



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

                calc_greenspace(img)
            except ServiceException as e:
                print e
        else:
            #print record[CITY_NAME], box, "not within our data range!"


if __name__ == '__main__':
    main()
