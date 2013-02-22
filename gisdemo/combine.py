"""
Likely not useful to anyone else, but just putting it out there.

This script will take a directory of GeoTIFFs and merge them together without issues.
This script simply decompresses the files, runs nearblack to remove pseudo-black borders caused by compression, and then uses gdalwarp to stitch the files together.

The script is designed to use the minimal amount of disk space possible -- it cleans up each file after decompression and continually merges with a master image.
"""

import os
import shutil
from subprocess import Popen, PIPE, STDOUT
import tempfile
import settings
from greencitieslog import log
#
# I think _uncompress, _stitch_with_master and _remove_nearblack are now dead code...
#
def _uncompress(file_path):
    cmd = '/usr/local/bin/gdal_translate %s %s.uncompressed.tif' % (file_path, file_path)
    log("Calling:",cmd)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()
    out,err = p.communicate()
    log("Gdal_transulate", out, err)
    assert p.returncode == 0, "Uncompress Failed"
    return '%s.uncompressed.tif' % file_path


## def _remove_nearblack(file_path):
##     cmd = '/usr/bin/nearblack -near 20 %s' % file_path
##     p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
##     p.wait()
##     output = p.stdout.read()
##     log(output)
##     assert p.returncode == 0, "GDalWarp Failed"
    


## def _stitch_with_master(file_path, master_path):
##     master_path = master_path.strip()
##     if not os.path.exists(master_path):
##         log("First file")
##         shutil.copyfile(file_path, master_path)
##         return
##     else:
##         log(os.path.exists(master_path))

##     tmp_master  = master_path.strip()+".temp.tif"
##     cmd = '/usr/bin/gdalwarp -multi -srcnodata 0 %s %s %s' % (file_path, master_path, tmp_master)
##     p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
##     p.wait()
##     output = p.stdout.read()
##     assert p.returncode == 0, "GDalWarp Failed"
##     log(output)
##     shutil.copyfile(tmp_master, master_path)
##     os.remove(tmp_master)

import gcswift

def _compose_tiff(new, path):
    master_path = path + "/"+new + ".tif"
    #  "in _compose_tiff, master is " + master_path

    myFiles = []
    for filename in sorted(os.listdir(path)):
        file_path = os.path.join(path, filename)
        uncompressed_file = _uncompress(file_path)
        myFiles.append(uncompressed_file)
        # print "decompressed file is " + uncompressed_file + " for compressed file " + file_path

    mergeCmd = '/usr/local/bin/gdal_merge.py -n -9999 -a_nodata -9999 -of GTIFF -o '
    mergeCmd += master_path
    for filename in myFiles:
        mergeCmd += ' ' + filename

    log("Merging..." + mergeCmd)
    # print "Merging..." + mergeCmd

    p = Popen(mergeCmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()
    output = p.stdout.read()
    assert p.returncode == 0, "GDalMerge Failed"
    log(output)
    return master_path

def grab_pathrow_band_time(name):
    s1 = name.split('.')
    band = s1[2]
    s2 = s1[0].split("_")
    rp = s2[0]
    time = s2[1][3:]
    _type = s2[1][:3]
    rc = (rp, band, time, _type)
    return rc


def combine_bands(allfiles, file_manager, gid="new"):
    target = []
    dirName = gcswift.get_dir_name(allfiles[0])
    assert dirName == file_manager.tmp_file_dir, "band directory " + dirName + " ought to be equal to " + file_manager.tmp_file_dir
    if gid != "new" and os.path.exists(dirName + "/" + gid+"_b03.tif"):
        prefix = dirName + "/" + gid
        return [prefix + "_b03.tif", prefix + "_b04.tif", prefix + "_b07.tif"]

    
    assert dirName == file_manager.tmp_file_dir, "band directory " + dirName + " ought to be equal to " + file_manager.tmp_file_dir

    for full_name in allfiles:
        fname = gcswift.get_raw_file_name(full_name)
        info = grab_pathrow_band_time(fname)
        if info[3] != '7dt' and info[3] != '5dt':
            log("Skipping non-landsat 5/7 image" + fname)
        else:
            target.append((fname, info))
            
    cwd = os.getcwd()
    os.chdir(dirName)

    # all operations now are local to dirName
    
    temps = {'b03':tempfile.mkdtemp(prefix='landsatb03', dir=file_manager.tmp_file_dir),
             'b04':tempfile.mkdtemp(prefix='landsatb04', dir=file_manager.tmp_file_dir),
             'b07':tempfile.mkdtemp(prefix='landsatb07', dir=file_manager.tmp_file_dir)}

    for f in target:
        shutil.copy(f[0], temps[f[1][1]]+"/"+f[0])

    done = []
    for d in temps.items():
        new = _compose_tiff(gid+d[0], d[1])
        done.append(new.split('/')[-1])
        shutil.copy(new,".")
        shutil.rmtree(d[1])
    # return done
    os.chdir(cwd)
    # Return the absolute paths
    result = []
    for item in done:
        result.append(dirName + "/" + item)
    return result


## def combine_single(allfiles, gid="new"):
##     target = []
##     for f in allfiles:
##         if 'grass' in f:
##             target.append(f)

##     temps = {'all':tempfile.mkdtemp(prefix='landsatb03')}

##     for f in target:
##         shutil.copy(f, temps['all']+"/"+f)

##     done = []
##     for d in temps.items():
##         new = _compose_tiff(gid+d[0], d[1])
##         done.append(new.split('/')[-1])
##         shutil.copy(new,".")
##         shutil.rmtree(d[1])
##     return done

def test_combine():

    test_files = ['p011r031_5dt20050724.SR.b03.tif.gz', 'p011r031_5dt20050724.SR.b04.tif.gz', 'p011r031_5dt20050724.SR.b07.tif.gz', 'p012r030_7dt20061014.SR.b03.tif.gz', 'p012r030_7dt20061014.SR.b04.tif.gz', 'p012r030_7dt20061014.SR.b07.tif.gz', 'p012r031_7dt20060928.SR.b03.tif.gz', 'p012r031_7dt20060928.SR.b04.tif.gz', 'p012r031_7dt20060928.SR.b07.tif.gz', 'p013r030_5dt20050924.SR.b03.tif.gz', 'p013r030_5dt20050924.SR.b04.tif.gz', 'p013r030_5dt20050924.SR.b07.tif.gz']

    assert grab_pathrow_band_time(test_files[0]) == ('p011r031','b03', '20050724', '5dt'), "Problem parsing pathrow band"
    assert grab_pathrow_band_time(test_files[1]) == ('p011r031','b04', '20050724', '5dt'), "Problem parsing pathrow band"
    assert grab_pathrow_band_time(test_files[11]) == ('p013r030','b07', '20050924', '5dt'), "Problem parsing pathrow band"


    # combine_bands(test_files)


