from osgeo import osr, gdal
from gdalconst import *
import os


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
for f in os.listdir(dir):
    if f[-3:] == "tif":
        file = dir + f
        lat =  getLatLon(file)[1]

        if lat < 55:
            print "Keep", file

        else:    
            print "Trash", file


