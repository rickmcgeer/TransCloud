import psycopg2


# database constants
DB_USER = "stredger"#"root"
DB_PASS = "swick"#root"
GIS_DATABASE = "gisdemo"#"world"
PY2PG_TIMESTAMP_FORMAT = "YYYY-MM-DD HH24:MI:SS:MS"

CITY_TABLE = {'canada':"cities", 'us':"us_cities", 'all':"map"}
ID_COL = "gid"
NAME_COL = "name"
GEOM_COL = "the_geom"
GREEN_COL = "greenspace"

IMG_TABLE = "times"#"processed"
IMG_NAME_COL = "file_path"
START_T_COL = "process_start_time"
END_T_COL = "process_end_time"
SERV_NAME_COL = "server_name"


class pgConnection:
    
    conn = None:
    cur = None:

    def __init__(self):
        
