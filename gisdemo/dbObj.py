import psycopg2
import settings

PY2PG_TIMESTAMP_FORMAT = "YYYY-MM-DD HH24:MI:SS:MS"

cluster_query =  ""
CITY_TABLE = {'canada':"cities", 'us':"us_cities", 'all':"map",}
ID_COL = "map.gid"
NAME_COL = "map.name"
GEOM_COL = "map.the_geom"
GREEN_COL = "map.greenspace"


IMG_TABLE = "processed"
GID_COL = "gid"
IMG_NAME_COL = "file_path"
START_T_COL = "process_start_time"
END_T_COL = "process_end_time"
SERV_NAME_COL = "server_name"
CLUSTER_COL = "cluster"

IMG_GID_COL = "processed.gid"
IMG_IMG_NAME_COL = "processed.file_path"
IMG_START_T_COL = "processed.process_start_time"
IMG_END_T_COL = "processed.process_end_time"
IMG_SERV_NAME_COL = "processed.server_name"
IMG_CLUSTER_COL = "processed.cluster"

# projection SRID
WSG84 = "4326"
GEOG = WSG84

#to support cgi queries on cluster status
# create table cgi_query_values_history
# query_time timestamp without time zone,
# query_id serial,
# cluster_name character varying(256),
# nodes integer,
# workers integer,
# cities integer

CGI_TABLE = 'cgi_query_values_history'
CGI_TIME_COL = 'query_time'
CGI_ID_COL = 'query_id'
CGI_CLUSTER_COL = 'cluster_name'
CGI_NODE_COL = 'nodes'
CGI_WORKERS_COL = 'workers'
CGI_CITIES_COL = 'cities'


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
        except psycopg2.OperationalError as e:
            print "Failed to connect to database:", str(e)
            print "host", settings.DB_HOST, "database", settings.GIS_DATABASE, "user", settings.DB_USER, "password", settings.DB_PASS
            raise # may want to raise some other error or somebody?


    def __del__(self):
        self.conn.close()


    def createSelectQuery(self, region, limit):
        """ Returns an sql select statement as a string which gets
        records from the table containing the specified region
        with no greenspace value
        """
        assert type(region)==int
        assert 1 <= region <= 4

#select fname 
#from (select ST_Transform(the_geom, 4326) as the_geom from by_continent where id = 1 ) as map , tiff4326 
#where ST_Intersects(map.the_geom, tiff4326.the_geom);


        select = ID_COL+", "+NAME_COL+", "\
            "ST_AsText(ST_ConvexHull(ST_Transform("+GEOM_COL+","+GEOG+"))),"\
            "ST_XMin(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_YMin(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_XMax(ST_Transform("+GEOM_COL+","+GEOG+")),"\
            "ST_YMax(ST_Transform("+GEOM_COL+","+GEOG+"))"

        _from  = " FROM " + "(select ST_Transform(the_geom, 4326) as the_geom from by_continent where id = %d ) as cluster, map" % (region)

        # keep WHERE in here incase we dont want a where clause
        #where = " WHERE name LIKE 'VIC%' OR name LIKE 'VAN%' OR name LIKE 'EDM%'"
        #where = " WHERE name LIKE 'HOPE'"
        #where = " WHERE gid=18529" # this is victoria
        #where = " WHERE gid = 19804" 
        #where = " WHERE gid = 25237" # boston
        #where = " WHERE gid > 19093 AND gid < 19099" # this is boston
        #where = " WHERE name LIKE 'BOSTON' OR name LIKE 'LONDON' OR name LIKE 'CANCUN'"
        #where = " WHERE name='KOLBASOVKA'"
        where = " WHERE "+GREEN_COL+"=0" + \
        "AND " + "ST_Intersects( ST_Transform(map.the_geom, 4326), cluster.the_geom)"
		
        limit = " LIMIT " + str(limit)
        #limit = ""

        return "SELECT " + select + _from + where + limit + ";"

    
    def createCoordQuery(self, a, b):
        """ Returns an sql query to get the distance in m between 
        2 lat long points """
        assert False, "Maybe this is not used?"
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

        greenTbl = "UPDATE map" + " SET greenspace =" + str(greenspace) + " WHERE gid = " + str(gid) + ";"

        imageTbl = "UPDATE " + IMG_TABLE +" SET " + IMG_NAME_COL + "='" + imgName+ "', "\
            +START_T_COL+"="+st_time+", "\
            +END_T_COL+"="+end_time+", "\
            +SERV_NAME_COL+"='"+servName+"', "\
            +CLUSTER_COL+"='"+region+"'"\
            +" WHERE gid" + "=" + str(gid) + ";"

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

    def get_workers_and_cities(self, cluster_name):
        """Called by getCGIValues to get the total number of workers in a cluster and total number of cities processed.
        Returns a pair(workers, cities).  Broken out separately for testing...
        """
        get_current_workers_query = "SELECT count(distinct " + SERV_NAME_COL + ") FROM " + IMG_TABLE
        get_total_cities_query = "SELECT count(*) FROM " + IMG_TABLE + " WHERE " + SERV_NAME_COL + " IS NOT NULL "
        if cluster_name != 'total':
            get_current_workers_query += " WHERE " + CLUSTER_COL +"='" + cluster_name +"'"
            get_total_cities_query += " AND " + CLUSTER_COL +"='" + cluster_name +"'"
        workers = int(self.performSelect(get_current_workers_query)[0][0])
        cities = int(self.performSelect(get_total_cities_query)[0][0])
        return (workers, cities)

    def update_cgi_values_table(self, cluster_name, workers, nodes, cities):
        update_statement = "INSERT into %s (%s, %s, %s, %s) VALUES ('%s', %d, %d, %d)" % \
        (CGI_TABLE, CGI_CLUSTER_COL, CGI_WORKERS_COL, CGI_NODE_COL, CGI_CITIES_COL, cluster_name, workers, nodes, cities)
        # print "Performing " + update_statement
        self.performUpdate(update_statement)

    def get_last_cgi_query(self):
        query_statement = "select query_id from cgi_query_values_history order by query_id desc limit 1"
        result = self.performSelect(query_statement)
        resultTuple = result[0]
        return resultTuple[0]
        

    def get_and_update_CGIValues(self, cluster_name='total'):
        (workers, cities) = self.get_workers_and_cities(cluster_name)
        self.update_cgi_values_table(cluster_name, workers, workers, cities)
        query_statement = "SELECT %s, %s, %s FROM %s WHERE  %s='%s' ORDER BY %s" % \
        (CGI_NODE_COL, CGI_WORKERS_COL, CGI_CITIES_COL, CGI_TABLE, CGI_CLUSTER_COL, cluster_name, CGI_ID_COL)
        result = self.performSelect(query_statement)
        worker_results =[0]
        cities_results = [0]
        nodes_results = [0]
        for (node_num, worker_num, city_num) in result:
            worker_results.append(worker_num)
            cities_results.append(city_num)
            nodes_results.append(node_num)
        
        return {'cities':cities_results, 'workers':worker_results, 'nodes':nodes_results}

    # when we get the daemon running delete the calls to get_and_update_CGIValues
    
    def getCGIValues(self, cluster_name='total'):
        """Called by get_data in cgi_bin to get a history of the computation
        on cluster_name; total is a special cluster which means everybody.
        Returns a dictionary of lists suitable for json encoding: {nodes:[list_of_node_values],
        cities:[list_of_cities_values], workers:[list_of_workers]}
        """
        cluster_data = self.get_and_update_CGIValues(cluster_name)
        total_data = self.get_and_update_CGIValues('total')
        return {'site_name':cluster_name,
                'cities':cluster_data['cities'],
                'workers':cluster_data['workers'],
                'nodes':cluster_data['nodes'],
                'cities_total':total_data['cities'],
                'workers_total':total_data['workers'],
                'nodes_total':total_data['nodes']
                }

    def getLast10Cities(self):
        """Called by get_last_10_cities in cgi_bin to get the last 10 cities processed.
           Returns a list of  gid: <city id>, name:<city name>
        """
        query_statement = "select processed.gid, map.name from processed inner join map on processed.gid = map.gid where processed.process_end_time is not null order by process_end_time desc limit(10)"
        result = self.performSelect(query_statement)
        webResult = []
        for (gid, name) in result: webResult.append({'city_id': gid, 'city_name':name})
        return webResult

    def getTop10Cities(self):
        """Called by get_last_10_cities in cgi_bin to get the last 10 cities processed.
           Returns a list of  gid: <city id>, name:<city name>
        """
        query_statement = "select gid, name from map where greenspace is not null order by greenspace desc limit 10"
        result = self.performSelect(query_statement)
        webResult = []
        for (gid, name) in result: webResult.append({'city_id': gid, 'city_name':name})
        return webResult
    
        
        


        

def test_db():
    try:
        db = pgConnection()
    except Exception as e:
        assert False, "Database connection failed:"+str(e)
    assert db!=None, "Database returned no handle."

    q = db.createClusterQuery("SRID=4326;POINT(-43.23456 72.4567772)")
    result =  db.performSelect(q)[0]

    assert result[0] == 1
    assert result[1] == 'north_america'
    
    select_query = db.createSelectQuery(1, 10)
    
    assert len(select_query) > 0 and "SELECT" in select_query and ";" in select_query, "poorly formed database query"
    records = db.performSelect(select_query)
    assert len(records) == 10, "Did not get the right number of cities back, got %d instead of 10\nQuery:\n%s"%(len(records), select_query)
