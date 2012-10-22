#!/usr/bin/env python
import os
import gzip
import commands
import re
import psycopg2
import sys, traceback
import datetime
import hashlib
import subprocess
import settings

# database constants
DB_USER = "postgres"
DB_PASS = ""
GIS_DATABASE = "world"
GIS_TAB = "tiff_rap"
DB_HOST= "10.0.0.16"
PATH = settings.TEMP_FILE_DIR + '/'

def log(*args):
    lf = sys.stderr
    msg = str(datetime.datetime.now()) + ": "
    for arg in args:
        msg += str(arg) + " "
    lf.write(msg+'\n')

class line_matcher:
    def __init__(self, regexp, handler):
        self.regexp  = re.compile(regexp)
        self.handler = handler

def create_match():
    matchers = []
    matchers.append(line_matcher(r'Upper\s*Left\s*\(\s*(\S+.\S+,\s*\S+.\S+)\)\s+', handle_up_left))
    matchers.append(line_matcher(r'Lower\s*Left\s*\(\s*(\S+.\S+,\s*\S+.\S+)\)\s+', handle_low_left))
    matchers.append(line_matcher(r'Upper\s*Right\s*\(\s*(\S+.\S+,\s*\S+.\S+)\)\s+', handle_up_right))
    matchers.append(line_matcher(r'Lower\s*Right\s*\(\s*(\S+.\S+,\s*\S+.\S+)\)\s+', handle_low_right))
    matchers.append(line_matcher(r'\s*AUTHORITY\[\"EPSG\",\"(\S+)\"', handle_epsg))
    return matchers       
    
def handle_up_left(line, result, polygon):
    polygon['Upper_Left'] = result.group(1)

def handle_low_left(line, result, polygon): 
    polygon['Lower_Left'] = result.group(1)

def handle_up_right(line, result, polygon):
    polygon['Upper_Right'] = result.group(1)

def handle_low_right(line, result, polygon):
    polygon['Lower_Right'] = result.group(1)
    
def handle_epsg(line, result, polygon):
    polygon['EPSG'] = result.group(1)
    
def get_poly(zfilename):
    full_name = PATH + zfilename
    f = gzip.GzipFile(full_name, 'rb')
    decompresseddata = f.read()
    f.close()
    tempTifFileName = settings.TEMP_FILE_DIR + "/tmp.tif"
    outFile = open(tempTifFileName, "w")
    outFile.write(decompresseddata)
    outFile.close()
    out = commands.getoutput('gdalinfo ' + tempTifFileName)
    commands.getoutput('rm -f ' + tempTifFileName)
    commands.getoutput('rm -f ' + full_name)
        
    lines = out.split('\n')
    polygon = {}
    for line in lines:
        for m in matchers:
            result = m.regexp.match(line)                
            if result:
                m.handler(line, result, polygon)
                break
    return polygon  

def poly2wkt(poly):
    p1x = re.sub(r'\s', '', poly['Lower_Left'].split(',')[0])
    p1y = re.sub(r'\s', '', poly['Lower_Left'].split(',')[1])
    p2x = re.sub(r'\s', '', poly['Upper_Left'].split(',')[0])
    p2y = re.sub(r'\s', '', poly['Upper_Left'].split(',')[1])   
    p3x = re.sub(r'\s', '', poly['Upper_Right'].split(',')[0])
    p3y = re.sub(r'\s', '', poly['Upper_Right'].split(',')[1])
    p4x = re.sub(r'\s', '', poly['Lower_Right'].split(',')[0])
    p4y = re.sub(r'\s', '', poly['Lower_Right'].split(',')[1])
    wkt = 'POLYGON((' + str(p1x) + ' ' + str(p1y) + ', ' + str(p2x) + ' ' + str(p2y) + ', ' + str(p3x) + ' ' + str(p3y) + ', ' + str(p4x) + ' ' + str(p4y) + ', ' + str(p1x) + ' ' + str(p1y) + '))\', ' + poly['EPSG'] 
    return wkt  

def create_database(conn, cur):
    try:
        cur.execute("select exists(select * from information_schema.tables where table_name=%s)", (GIS_TAB,))
        if (cur.fetchone()[0] is False):        
            cur.execute('CREATE TABLE '+ GIS_TAB + ' (id serial PRIMARY KEY, "band" integer, "date" varchar(254), "fname" varchar(254));')
            cur.execute("SELECT AddGeometryColumn('" + GIS_TAB + "','the_geom','4326','POLYGON',2);")
            conn.commit()
    except psycopg2.ProgrammingError as e:
        log(e)
        conn.rollback()
            
def update_database(conn, cur, band, date, name, wkt):
    try:
        cur.execute("SELECT fname FROM " + GIS_TAB + " WHERE fname = " + str(name) + ";")
        exist = cur.fetchone()
        if (not exist):
            update = "INSERT INTO " + GIS_TAB + " (band, date, fname, the_geom)  VALUES (" + str(band) + "," + date + "," + str(name) + "," + " ST_Transform(ST_GeomFromText('" + wkt + "), 4326));"
            #print update
            cur.execute(update)
            conn.commit()
    except psycopg2.ProgrammingError as e:
        log("Failed to update database:", e)
        conn.rollback()

if __name__ == '__main__':   
    matchers = create_match()    
    #conn = psycopg2.connect(database=GIS_DATABASE, user=DB_USER, password=DB_PASS) 
    conn = psycopg2.connect(database=GIS_DATABASE, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()
    create_database(conn, cur) # only call for the first time
    
    command = ["swift", "-A",
           "http://swift.gcgis.trans-cloud.net:8080/auth/v1.0",
           "-U",
           "system:gis",
           "-K",
           "uvicgis"]
    containers = list(command)
    containers.append("list")
    p = subprocess.Popen(containers, stdout=subprocess.PIPE)
    p.wait()
    assert p.returncode == 0, "Failed on swift host %s with %s" % ("swift.gcgis.trans-cloud.net", p.communicate()[1])
    out, err = p.communicate()
   
    buckets = out.split("\n")  #[::-1]
    if len(sys.argv) > 1:
        target = sys.argv[1]   
        spot = 0
        for number, bucket in enumerate(buckets):
            if target in bucket:
                spot = number
                break
        buckets = buckets[spot:]            
           
    for line in buckets:   # testing!!!!!!!!!
        to_crawl = []
        try:
           if line[0] == "p":            
                new_command = list(containers)
                new_command.append(line)
                p = subprocess.Popen(new_command, stdout=subprocess.PIPE)
                p.wait()
                if p.returncode != 0:
                    print "skipping bucket", line
                    break
                out, err = p.communicate()    
                all_files =  out.split("\n")
                to_crawl.append((line, all_files[0], all_files))
                to_crawl = [f for f in to_crawl if f != ""]

                for files in to_crawl:
                    download_command = list(command)
                    download_command.append("download")
                    download_command.append(files[0])  # bucket number
                    download_command.append(files[1])  # first file name
                    print str(datetime.datetime.now()) + ": " + files[0]
                    print files[1]
                    print
                    rest = files[2]         # all rest of files
                    download_command.append("-o")
                    download_command.append(PATH+files[1])
                    p = subprocess.Popen(download_command, stdout=subprocess.PIPE)  # download the first file in the bucket
                    p.wait()
                    if p.returncode != 0:
                        print "skipping file", files[0], files[1]
                        break
                    out, err = p.communicate()
                
                    poly = get_poly(files[1])     
                    wkt = poly2wkt(poly)
                
                    for f in rest:
                        if (f != ""):
                            seg = f.split('.')
                            date = seg[0].split('_')[1][-8:]
                            band = int(seg[2][-2:])
                            name = "'" + seg[0] + '_' + seg[1] + '_' + seg[2] +"'" 
                            update_database(conn, cur, band, date, name, wkt)
        except Exception, e:
            print e            
    cur.close()
    conn.close()
