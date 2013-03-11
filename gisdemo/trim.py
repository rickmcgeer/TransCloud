import subprocess
import os
import re
import dbObj
import settings
from greencitieslog import log
import gcswift


def get_projection(fil):
    command = "gdalinfo " + fil
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    p.wait()
    assert p.returncode == 0, "Gdal info failed."
    out, err = p.communicate()
    auth = [x.strip() for x in out.split("\n") if 'AUTHORITY["' in x][-1]
    return auth.split('"')[3]
    

def reproject_shapefile(full_shapefile, shapefile, new_projcode, shapefile_tmpDir):
    os.mkdir(shapefile_tmpDir)
    new_fil = shapefile_tmpDir + "/"+ shapefile
    base,ext = shapefile.split(".")
    cmd =  'ogr2ogr -s_srs "EPSG:4326" -t_srs "EPSG:' + new_projcode + '" '  + new_fil  + " " + full_shapefile
    log("Running:", cmd)
    # print "Running: " + cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.wait()
    out, err = p.communicate()
    log("ogr2ogr said:", out, err)
    assert p.returncode == 0, "Reprojection failed - Probably a SRS missmatch..."
    return new_fil
    

def crop(shapefile_full, raster_full, raster2_full=None, raster3_full=None, prefix="new_", new_projcode=None, shapefile_tmpDir="tmp2"):
    shapefile = gcswift.get_raw_file_name(shapefile_full)
    raster = gcswift.get_raw_file_name(raster_full)
    layername =  shapefile.split(".")[0]
    if not new_projcode:
        new_projcode = get_projection(raster_full)
    new_shapefile = reproject_shapefile(shapefile_full, shapefile, new_projcode, shapefile_tmpDir)

    command = "ogrinfo  %s %s" % (new_shapefile,layername)
    # print "Getting shape info", command
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    # p.wait()
    out, err = p.communicate()
    #print out
    assert "Geometry: Polygon" in out, "Problem reading the shapefile"
    lines = out.split("\n")
    line = [x for x in lines if x.startswith("Extent: ")][0]
    bb = re.findall(r"[0-9.]*[0-9]+", line)
    bb = [bb[0], bb[3], bb[2], bb[1]]
    bb_str = " ".join(bb)
    dir_name = gcswift.get_dir_name(raster_full)
    full_prefix = dir_name + "/" + prefix

    command_prefix = "gdal_translate -projwin " + bb_str + " -of GTiff "
    command = command_prefix + raster_full + " " + full_prefix + raster
    # print "Crop command", command
  
  
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)

    if raster2_full:
        raster2 = gcswift.get_raw_file_name(raster2_full)
        command2 = command_prefix + raster2_full + " "+ full_prefix+raster2
        # print "Crop command", command2
        q = subprocess.Popen(command2, shell=True, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)

    if raster3_full:
        raster3 = gcswift.get_raw_file_name(raster3_full)
        command3 = command_prefix + raster3_full + " "+full_prefix+raster3
        # print "Crop command", command3
        r = subprocess.Popen(command3, shell=True, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)


    p.wait()
    assert p.returncode == 0, "Failed with %s"%(p.communicate()[0])
    if raster2_full:
        q.wait()
        assert q.returncode == 0
    if raster3_full:
        r.wait()
        assert r.returncode == 0
        
    out, err = p.communicate()
    
    # print "done"
    # print out,err
    

    
def test():
    rc = subprocess.call(["which","ogrinfo"])
    assert rc==0, "Ogrinfo not installed"
    rc = subprocess.call(["which","gdal_translate"])
    assert rc==0, "Gdal-bin not installed"



def getShapefile(tmp_dir_name, gid):
    
    shpname = tmp_dir_name + "/" + str(gid)+'.shp'

    if os.path.exists(shpname):
        return shpname

    pginfo = "host="+settings.DB_HOST + " user="+settings.DB_USER\
           + " dbname="+settings.GIS_DATABASE

    sql = "SELECT the_geom FROM "+dbObj.CITY_TABLE['all']+" WHERE GID = "+str(gid)+";"

    command = 'ogr2ogr -f "ESRI Shapefile" ' + shpname + ' PG:"'+pginfo +'" -sql "'+sql+'"'

    # print command

    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)
    p.wait()
    assert p.returncode == 0, "Failed with %s"%(p.communicate()[1])
    assert os.path.exists(shpname)

    return shpname


def test_trim():
    assert get_projection("p145r032_7dt20060730.SR.b03.tif") == "32644", "Did not get the correct projection"
    
    assert reproject_shapefile("19094.shp", "32617", "tmp2") == "./tmp2/19094.shp"

    crop("19094.shp", "p019r026_7dt20050708.SR.b03.tif", prefix="new_", shapefile_tmpDir="tmp2")

    #getShapefile(23839)

