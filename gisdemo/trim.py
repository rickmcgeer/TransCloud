import subprocess
import os
import re
#import dbObj

def get_projection(fil):
    command = "gdalinfo " + fil
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    p.wait()
    assert p.returncode == 0
    out, err = p.communicate()
    auth = [x.strip() for x in out.split("\n") if 'AUTHORITY["' in x][-1]
    return auth.split('"')[3]
    

def reproject_shapefile(shapefile, new_projcode):
    base,ext = shapefile.split(".")
    cmd =  'ogr2ogr -overwrite -s_srs "EPSG:4326" -t_srs "EPSG:' + new_projcode + '" tmp2 ' + shapefile
    print cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.wait()
    assert p.returncode == 0, "Reprojection failed - Probably a SRS missmatch..."
    out, err = p.communicate()
    print out
    return "./tmp2/"+shapefile
    

def crop(shapefile, raster, raster2=None, raster3=None, prefix="new_"):
    layername =  shapefile.split(".")[0]
    new_projcode = get_projection(raster)
    new_shapefile = reproject_shapefile(shapefile, new_projcode)

    command = "ogrinfo  %s %s" % (new_shapefile,layername)
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    p.wait()
    out, err = p.communicate()
    print out
    assert "Geometry: Polygon" in out, "Problem reading the shapefile"
    lines = out.split("\n")
    line = [x for x in lines if x.startswith("Extent: ")][0]
    bb = re.findall(r"[0-9.]*[0-9]+", line)
    bb = [bb[0], bb[3], bb[2], bb[1]]
    bb_str = " ".join(bb)

    command_prefix = "gdal_translate -projwin " + bb_str + " -of GTiff "
    command = command_prefix + raster + " "+ prefix+raster
  
  
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)

    if raster2:
        command2 = command_prefix + raster2 + " "+prefix+raster2
        q = subprocess.Popen(command2, shell=True, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)

    if raster3:
        command3 = command_prefix + raster3 + " "+prefix+raster3
        r = subprocess.Popen(command3, shell=True, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)


    p.wait()
    assert p.returncode == 0, "Failed with %s"%(p.communicate()[0])
    if raster2:
        q.wait()
        assert q.returncode == 0
    if raster3:
        r.wait()
        assert r.returncode == 0
        
    out, err = p.communicate()
    
    print "done"
    print out,err
    

    
def test():
    rc = subprocess.call(["which","ogrinfo"])
    assert rc==0, "Ogrinfo not installed"
    rc = subprocess.call(["which","gdal_translate"])
    assert rc==0, "Gdal-bin not installed"



def getShapefile(gid):
    
    shpname = str(gid)+'.shp'

    if os.path.exists(shpname):
        return shpname

    pginfo = "host="+dbObj.DB_HOST + " user="+dbObj.DB_USER\
           + " dbname="+dbObj.GIS_DATABASE

    sql = "SELECT the_geom FROM "+dbObj.CITY_TABLE['all']+" WHERE GID = "+str(gid)+";"

    command = 'ogr2ogr -f "ESRI Shapefile" ' + shpname + ' PG:"'+pginfo +'" -sql "'+sql+'"'

    print command

    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)
    p.wait()
    assert p.returncode == 0, "Failed with %s"%(p.communicate()[1])
    assert os.path.exists(shpname)

    return shpname


if __name__ == "__main__":
    print ">>"
    assert get_projection("p145r032_7dt20060730.SR.b03.tif") == "32644", "Did not get the correct projection"
    
    assert reproject_shapefile("19094.shp", "32617") == "./tmp2/19094.shp"

    crop("19094.shp", "p019r026_7dt20050708.SR.b03.tif", prefix="new_")

    #getShapefile(23839)


test()


