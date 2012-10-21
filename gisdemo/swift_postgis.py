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
GIS_TAB = "tiff"
DB_HOST= "198.55.37.15"
tiff_created = 0

def craler():
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
    out, err = p.communicate()

    to_crawl = []
    buckets = out.split("\n")
    for line in buckets[:10]:   # testing!!!!!!!!!
        if line[0] == "p":            
            new_command = list(containers)
            new_command.append(line)
            p = subprocess.Popen(new_command, stdout=subprocess.PIPE)
            p.wait()
            out, err = p.communicate()    
            for files in out.split("\n"):
                to_crawl.append((line, files))

    to_crawl[:] = [f for f in to_crawl if f != ""]
    to_crawl = to_crawl[:10]   # testing!!!!!!!!!

    for files in to_crawl:
        download_command = list(command)
        download_command.append("download")
        download_command.append(files[0])
        download_command.append(files[1])
        download_command.append("-o")
        download_command.append(settings.TEMP_FILE_DIR + "/" +files[1])
        p = subprocess.Popen(download_command, stdout=subprocess.PIPE)
        p.wait()
        out, err = p.communicate()
        
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
        
def handle_up_left(line, result, polygon):
    polygon['Upper_Left'] = result.group(1)

def handle_low_left(line, result, polygon): 
    polygon['Lower_Left'] = result.group(1)

def handle_up_right(line, result, polygon):
    polygon['Upper_Right'] = result.group(1)

def handle_low_right(line, result, polygon):
    polygon['Lower_Right'] = result.group(1)
    
#def handle_band(line, result, polygon):
#    polygon['Band'] = result.group(1)
    
def get_poly(zfilename):
    full_name = path + zfilename
    f = gzip.GzipFile(full_name, 'rb')
    decompresseddata = f.read()
    f.close()
    tempTIFFile = settings.TEMP_FILE_DIR + "/tmp.tif"
    outFile = open(tempTIFFile, "w")
    outFile.write(decompresseddata)
    outFile.close()
    out = commands.getoutput('gdalinfo ' + tempTIFFile)
    commands.getoutput('rm -f ' + tempTIFFile)
        
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
    print p1x+', '+p1y
    p2x = re.sub(r'\s', '', poly['Upper_Left'].split(',')[0])
    p2y = re.sub(r'\s', '', poly['Upper_Left'].split(',')[1])
    print p2x+', '+p2y    
    p3x = re.sub(r'\s', '', poly['Upper_Right'].split(',')[0])
    p3y = re.sub(r'\s', '', poly['Upper_Right'].split(',')[1])
    print p3x+', '+p3y
    p4x = re.sub(r'\s', '', poly['Lower_Right'].split(',')[0])
    p4y = re.sub(r'\s', '', poly['Lower_Right'].split(',')[1])
    print p4x+', '+p4y
    print
    wkt = 'POLYGON((' + str(p1x) + ' ' + str(p1y) + ', ' + str(p2x) + ' ' + str(p2y) + ', ' + str(p3x) + ' ' + str(p3y) + ', ' + str(p4x) + ' ' + str(p4y) + ', ' + str(p1x) + ' ' + str(p1y) + '))'
    return wkt

def create_database(conn, cur):
    try:
        cur.execute("select exists(select * from information_schema.tables where table_name=%s)", (GIS_TAB,))
        if (cur.fetchone()[0] is False):        
            cur.execute('CREATE TABLE '+ GIS_TAB + ' (id serial PRIMARY KEY, "band" integer, "date" varchar(254), "fname" varchar(254));')
            cur.execute("SELECT AddGeometryColumn('" + GIS_TAB + "','the_geom','4202','POLYGON',2);")
            conn.commit()
    except psycopg2.ProgrammingError as e:
        log(e)
            
def update_database(conn, cur, band, date, name, geom):
    try:
        update = "INSERT INTO " + GIS_TAB + " (band, date, fname, the_geom)  VALUES (" + str(band) + "," + date + "," + str(name) + "," + " ST_GeomFromText('" + wkt + "',4202));"
        cur.execute(update)
        conn.commit()
    except psycopg2.ProgrammingError as e:
        log("Failed to update database:", e)
        
if __name__ == '__main__':
    #craler()
    
    path = settings.TEMP_FILE_DIR + '/'
    tiff_gz = [f for f in os.listdir(path) if f.endswith('.tif.gz')]    
    matchers = []
    matchers.append(line_matcher(r'Upper\s*Left\s*\(\s*(\S+.\S+,\s*\S+.\S+)\)', handle_up_left))
    matchers.append(line_matcher(r'Lower\s*Left\s*\(\s*(\S+.\S+,\s*\S+.\S+)\)', handle_low_left))
    matchers.append(line_matcher(r'Upper\s*Right\s*\(\s*(\S+.\S+,\s*\S+.\S+)\)', handle_up_right))
    matchers.append(line_matcher(r'Lower\s*Right\s*\(\s*(\S+.\S+,\s*\S+.\S+)\)', handle_low_right))
    
    # conn = psycopg2.connect(database=GIS_DATABASE, user=DB_USER, password=DB_PASS)
    conn = psycopg2.connect(database=GIS_DATABASE, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()
    create_database(conn, cur) # only call for the first time!!!!!!!!

    for zfilename in tiff_gz:  
        poly = get_poly(zfilename)
        seg = zfilename.split('.')
        date = seg[0].split('_')[1][-8:]
        band = int(seg[2][-2:])
        name = "'" + seg[0] + '_' + seg[1] + '_' + seg[2] +"'"     
        wkt = poly2wkt(poly)
        update_database(conn, cur, band, date, name, wkt)
    
    cur.close()
    conn.close()
