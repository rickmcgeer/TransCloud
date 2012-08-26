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


def _uncompress(file_path):
    cmd = '/usr/bin/gdal_translate %s %s.uncompressed.tif' % (file_path, file_path)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read()
    p.wait()
    assert p.returncode == 0, "GDalWarp Failed"
    print output


def _remove_nearblack(file_path):
    cmd = '/usr/bin/nearblack -near 20 %s' % file_path
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read()
    p.wait()
    assert p.returncode == 0, "GDalWarp Failed"
    print output


def _stitch_with_master(file_path, master_path):
    master_path = master_path.strip()
    if not os.path.exists(master_path):
        print "First file"
        shutil.copyfile(file_path, master_path)
        return
    else:
        print os.path.exists(master_path)

    tmp_master  = master_path.strip()+".temp.tif"
    cmd = '/usr/bin/gdalwarp -multi -srcnodata 0 %s %s %s' % (file_path, master_path, tmp_master)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()
    output = p.stdout.read()
    assert p.returncode == 0, "GDalWarp Failed"
    print output
    shutil.copyfile(tmp_master, master_path)
    os.remove(tmp_master)


def _compose_tiff(new, path):
    master_path = path + "/"+new + ".tif"

    for filename in sorted(os.listdir(path)):

        file_path = os.path.join(path, filename)

        print "Uncompressing...%s" % file_path
        _uncompress(file_path)

        print "Removing near black...%s" % file_path
        _remove_nearblack("%s.uncompressed.tif" % file_path)

        print "Stitching with master...%s" % file_path
        _stitch_with_master("%s.uncompressed.tif" % file_path, master_path)

        print "Stitched with master %s!" % file_path
        os.remove("%s.uncompressed.tif" % file_path)

    #return new + ".tif"
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


def combine_bands(allfiles, gid="new"):
    target = []
    if gid != "new" and os.path.exists(gid+"_b03.tif"):
        return [gid+"_b03.tif", gid+"_b04.tif", gid+"_b07.tif"]

    for fname in allfiles:
        info = grab_pathrow_band_time(fname)
        if info[3] != '7dt':
            print "Skipping non-landsat 7 image", fname
        else:
            target.append((fname, info))

    temps = {'b03':tempfile.mkdtemp(prefix='landsatb03'),
             'b04':tempfile.mkdtemp(prefix='landsatb04'),
             'b07':tempfile.mkdtemp(prefix='landsatb07')}

    for f in target:
        shutil.copy(f[0], temps[f[1][1]]+"/"+f[0])

    done = []
    for d in temps.items():
        new = _compose_tiff(gid+d[0], d[1])
        done.append(new.split('/')[-1])
        shutil.copy(new,".")
        shutil.rmtree(d[1])
    return done


def combine_single(allfiles, gid="new"):
    target = []
    for f in allfiles:
        if 'grass' in f:
            target.append(f)

    temps = {'all':tempfile.mkdtemp(prefix='landsatb03')}

    for f in target:
        shutil.copy(f, temps['all']+"/"+f)

    done = []
    for d in temps.items():
        new = _compose_tiff(gid+d[0], d[1])
        done.append(new.split('/')[-1])
        shutil.copy(new,".")
        shutil.rmtree(d[1])
    return done

if __name__ == "__main__":

    #test_files = ['p011r031_5dt20050724.SR.b03.tif.gz', 'p011r031_5dt20050724.SR.b04.tif.gz', 'p011r031_5dt20050724.SR.b07.tif.gz', 'p012r030_7dt20061014.SR.b03.tif.gz', 'p012r030_7dt20061014.SR.b04.tif.gz', 'p012r030_7dt20061014.SR.b07.tif.gz', 'p012r031_7dt20060928.SR.b03.tif.gz', 'p012r031_7dt20060928.SR.b04.tif.gz', 'p012r031_7dt20060928.SR.b07.tif.gz', 'p013r030_5dt20050924.SR.b03.tif.gz', 'p013r030_5dt20050924.SR.b04.tif.gz', 'p013r030_5dt20050924.SR.b07.tif.gz']

    test_files = ['p012r030_7dt20061014.SR.b03.tif', 'p012r030_7dt20061014.SR.b04.tif', 'p012r030_7dt20061014.SR.b07.tif', 'p012r031_7dt20060928.SR.b03.tif', 'p012r031_7dt20060928.SR.b04.tif', 'p012r031_7dt20060928.SR.b07.tif']

    #assert grab_pathrow_band_time(test_files[0]) == ('p011r031','b03', '20050724', '5dt'), "Problem parsing pathrow band"
    #assert grab_pathrow_band_time(test_files[1]) == ('p011r031','b04', '20050724', '5dt'), "Problem parsing pathrow band"
    #assert grab_pathrow_band_time(test_files[11]) == ('p013r030','b07', '20050924', '5dt'), "Problem parsing pathrow band"


    combine_bands(test_files)
