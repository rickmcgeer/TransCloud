from osgeo import osr, gdal
from gdalconst import *
import os
import shutil

def convert_bytes(bytes):
    bytes = float(bytes)
    if bytes >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fT' % terabytes
    elif bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fG' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fM' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fK' % kilobytes
    else:
        size = '%.2fb' % bytes
    return size

def getLatLon(file):

    ds = gdal.Open(file, GA_ReadOnly )

    old_cs= osr.SpatialReference()
    old_cs.ImportFromWkt(ds.GetProjectionRef())

    # create the new coordinate system
    wgs84_wkt = """
    GEOGCS["WGS 84",
        DATUM["WGS_1984",
            SPHEROID["WGS 84",6378137,298.257223563,
                AUTHORITY["EPSG","7030"]],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.01745329251994328,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4326"]]"""
    new_cs = osr.SpatialReference()
    new_cs .ImportFromWkt(wgs84_wkt)

    # create a transform object to convert between coordinate systems
    transform = osr.CoordinateTransformation(old_cs,new_cs)

    width = ds.RasterXSize
    height = ds.RasterYSize
    gt = ds.GetGeoTransform()
    minx = gt[0]
    miny = gt[3] + width*gt[4] + height*gt[5] 
    maxx = gt[0] + width*gt[1] + height*gt[2]
    maxy = gt[3] 
    #get the coordinates in lat long
    latlong = transform.TransformPoint(minx,miny) 
    return latlong
dir = "/home/cmatthew/tmp/ls7tmp/"
_in = 0
out = 0
count = 0
tiff_count = 0

def move(file, dir, f):
    f_name = f[:-3]
    prefix_old = dir + f_name 
    prefix_new = dir + "higher_lats/" + f_name 
    print prefix_old, prefix_new
    
    print ">>", prefix_old+"tif", prefix_new+"tif"
    print ">>", prefix_old+"tifw", prefix_new+"tifw"
    print ">>", prefix_old+"aux", prefix_new+"aux"
#    print ">>", prefix_old+"txt", prefix_new+"txt"

    try:
        print "1", os.stat(prefix_old+"tif")
        print "2", os.stat(prefix_old+"tifw")
        print "3", os.stat(prefix_old+"aux")
#        print "4", os.stat(prefix_old+"txt")
    except:
        pass
    
    try:
        shutil.move(prefix_old+"tif", prefix_new+"tif")
    except:
        print "Failed:", prefix_old+"tif"
    try:
        shutil.move(prefix_old+"tifw", prefix_new+"tifw")
    except:
        print "Failed:", prefix_old+"tifw"
    try:
        shutil.move(prefix_old+"aux", prefix_new+"aux")
    except:
        "Failed:", prefix_old+"aux"
    # try:
    #     shutil.move(prefix_old+"txt", prefix_new+"txt")
    # except:
    #     "Failed:", prefix_old+"txt"


for f in os.listdir(dir):
    count += 1
    file = dir + f
    # print file
    if f[-3:] == "tif":
        tiff_count += 1
        try:
            lat =  getLatLon(file)[1]
        except:
            print "Skipping:", file
            continue
        if lat < 55:
            #print "Keep", file
            _in += os.path.getsize(file)
        else:
            out += os.path.getsize(file)
            move(file, dir, f)

print count, tiff_count, convert_bytes(_in), convert_bytes(out), convert_bytes(_in + out)
