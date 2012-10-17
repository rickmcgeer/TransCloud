import psycopg2
import settings

PY2PG_TIMESTAMP_FORMAT = "YYYY-MM-DD HH24:MI:SS:MS"

CITY_TABLE = {'canada':"cities", 'us':"us_cities", 'all':"map"}
ID_COL = "gid"
NAME_COL = "name"
GEOM_COL = "the_geom"
GREEN_COL = "greenspace"

IMG_TABLE = "processed"
IMG_NAME_COL = "file_path"
START_T_COL = "process_start_time"
END_T_COL = "process_end_time"
SERV_NAME_COL = "server_name"

# projection SRID
WSG84 = "4326"
GEOG = WSG84


class pgConnection:
    """  """
    conn = None

    def __init__(self):
        try:
            self.conn = psycopg2.connect(host=settings.DB_HOST,
                                         database=settings.GIS_DATABASE,
                                         user=settings.DB_USER,
                                         password=settings.DB_PASS)
        except psycopg2.ProgrammingError as e:
            print "Failed to connect to database:", str(e)
            raise # may want to raise some other error or somebody?


    def __del__(self):
        self.conn.close()


    def createSelectQuery(self, region):
        """ Returns an sql select statement as a string which gets
        records from the table containing the specified region
        with no greenspace value
        """

        select = ID_COL+", "+NAME_COL+", "\
            "ST_AsText(ST_ConvexHull(ST_Transform("+GEOM_COL+","+GEOG+"))),"\
            "ST_XMin(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_YMin(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_XMax(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_YMax(ST_Transform("+GEOM_COL+","+GEOG+"))"

        # keep WHERE in here incase we dont want a where clause
        #where = " WHERE name LIKE 'VIC%' OR name LIKE 'VAN%' OR name LIKE 'EDM%'"
        #where = " WHERE name LIKE 'HOPE'"
        #where = " WHERE gid=18529" # this is victoria
        #where = " WHERE gid = 19094" 
        #where = " WHERE gid = 25237" # boston
        #where = " WHERE gid > 19093 AND gid < 19099" # this is boston
        #where = " WHERE name LIKE 'BOSTON' OR name LIKE 'LONDON' OR name LIKE 'CANCUN'"
        where = " WHERE "+GREEN_COL+"=0"
        
		
        limit = " LIMIT 1000"
        #limit = ""

        return "SELECT " + select + " FROM " + CITY_TABLE[region] + where + limit + ";"

    
    def createCoordQuery(self, a, b):
        """ Returns an sql query to get the distance in m between 
        2 lat long points """

        if len(a) != len(b) or len(a) != 2:
            print "Can't form sql to get distance between points:", a, b
            return 

	# convert to well known text (wkt)
        a_wkt = "POINT(" + str(a[0]) + " " + str(a[1]) + ")"
        b_wkt = "POINT(" + str(b[0]) + " " + str(b[1]) + ")"
 
        query = "SELECT ST_Distance("\
            +"ST_GeogFromText('SRID="+GEOG+";"+a_wkt+"'),"\
            +"ST_GeogFromText('SRID="+GEOG+";"+b_wkt+"'));"

        return query

    def createClusterQuery(self,wkt):
       return "SELECT id, continent_name FROM by_continent WHERE ST_Intersects(by_continent.the_geom, ST_GeographyFromText('"+wkt+"'));"
       

    def performSelect(self, query):
        """ Perform 'query' in the database, then fetch the results
        if the query fails we log the error but continue execution.
        """

        try:
            cur = self.conn.cursor()
            cur.execute(query)
            # get our results
            records = cur.fetchall()
            cur.close()
            return records

        except psycopg2.ProgrammingError as e:
            print "Failed to fetch from database:", str(e)
            return []
 

    def createUpdateStmnt(self, greenspace, gid, name, start, 
                              end, imgName, servName, region):
        """ Returns an sql update statement as a string which sets
        the record with the matching gid's greenspace value, image 
        name, and timestamps
        """

        if name is None:
            name = ""

        # format the python timestamps into something postgres can understand
        st_time = "to_timestamp('"+str(start)+"', '"+PY2PG_TIMESTAMP_FORMAT+"')"
        end_time = "to_timestamp('"+str(start)+"', '"+PY2PG_TIMESTAMP_FORMAT+"')"

        greenTbl = "UPDATE "+CITY_TABLE[region]\
            +" SET "+GREEN_COL+"=" + str(greenspace)\
            +" WHERE "+ID_COL+"=" + str(gid) + ";"

        imageTbl = "UPDATE "+IMG_TABLE\
            +" SET "+IMG_NAME_COL+"='"+imgName+"', "\
            +START_T_COL+"="+st_time+", "\
            +END_T_COL+"="+end_time+", "\
            +SERV_NAME_COL+"='"+servName+"'"\
            +" WHERE "+ID_COL+"=" + str(gid) + ";"

        return greenTbl + imageTbl



    def performUpdate(self, query):
        """ Given a string continging sql, will perform the sql query.
        If the query fails log the error but continue execution.
        """

        try:
            cur = self.conn.cursor()
            cur.execute(query)
            # we must commit our transaction
            self.conn.commit()
            cur.close()

        except psycopg2.ProgrammingError as e:
            print "Failed to update database:", str(e)
            return


if __name__ == "__main__":
    db = pgConnection()
    q = db.createClusterQuery("SRID=4326;POINT(-43.23456 72.4567772)")
    assert db.performSelect(q)[0] == 1
    
    
