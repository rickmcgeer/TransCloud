#!/usr/bin/env python
import os
import gzip
import commands
import re
import psycopg2
import sys, traceback
import datetime

# database constants
DB_USER = "postgres"
DB_PASS = ""
GIS_DATABASE = "world"
GIS_TAB = "by_continent"
DB_HOST= "10.0.0.16"

def log(*args):
    lf = sys.stderr
    msg = str(datetime.datetime.now()) + ": "
    for arg in args:
        msg += str(arg) + " "
    lf.write(msg+'\n')

def create_database(conn, cur):
    try:
        cur.execute("select exists(select * from information_schema.tables where table_name=%s)", (GIS_TAB,))
        if (cur.fetchone()[0] is False):        
            cur.execute('CREATE TABLE '+ GIS_TAB + ' (id serial PRIMARY KEY, "continent_name" varchar(254));')
            cur.execute("SELECT AddGeometryColumn('" + GIS_TAB + "','the_geom','4326','POLYGON',2);")
            conn.commit()
    except psycopg2.ProgrammingError as e:
        log(e)
        conn.rollback()

def update_database(conn, cur, name, wkt):
    try:
        update = "INSERT INTO " + GIS_TAB + " (continent_name, the_geom)  VALUES (" + str(name) \
            + "," + " ST_GeomFromText('" + wkt + "', 4326));"
        print update
        cur.execute(update)
        conn.commit()
    except psycopg2.ProgrammingError as e:
        log("Failed to update database:", e)
        conn.rollback()
        
if __name__ == '__main__':     
    conn = psycopg2.connect(database=GIS_DATABASE, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()
    create_database(conn, cur)
    
    wkt = 'POLYGON((' + str(-180) + ' ' + str(85) + ', ' + str(-18) + ' ' + str(85) + ', ' \
        + str(-18) + ' ' + str(18) + ', ' + str(-180) + ' ' + str(18) + ', ' + str(-180) \
        + ' ' + str(85) + '))'
    update_database(conn, cur, "'north_america'", wkt)
    
    wkt = 'POLYGON((' + str(-18) + ' ' + str(85) + ', ' + str(60) + ' ' + str(85) + ', ' \
        + str(60) + ' ' + str(18) + ', ' + str(-18) + ' ' + str(18) + ', ' + str(-18) + ' ' \
        + str(85) + '))'
    update_database(conn, cur, "'europe'", wkt)
    
    wkt = 'POLYGON((' + str(-180) + ' ' + str(18) + ', ' + str(60) + ' ' + str(18) + ', ' \
        + str(60) + ' ' + str(-58) + ', ' + str(-180) + ' ' + str(58) + ', ' + str(-180) \
        + ' ' + str(18) + '))'
    update_database(conn, cur, "'south_america_africa'", wkt)
    
    wkt = 'POLYGON((' + str(60) + ' ' + str(85) + ', ' + str(180) + ' ' + str(85) + ', ' \
        + str(180) + ' ' + str(-85) + ', ' + str(60) + ' ' + str(-58) + ', ' + str(60) \
        + ' ' + str(85) + '))'
    update_database(conn, cur, "'asia_oceania'", wkt)
