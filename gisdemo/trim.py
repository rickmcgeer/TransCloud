import subprocess
import os
import re

def crop(shapefile, raster, raster2=None, raster3=None, prefix="new_"):
    command = "ogrinfo -so %s %s" % (shapefile, shapefile.split(".")[0])
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    p.wait()
    out, err = p.communicate()
    
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
    assert p.returncode == 0
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
    
    
test()


crop("test.shp", "p145r032_7dt20060730.SR.b03.tif", raster2="p145r032_7dt20060730.SR.b04.tif", raster3="p145r032_7dt20060730.SR.b07.tif", prefix="new_")


