import os
import sys
try:
    import psycopg2
    import png
except:
    print "Error: Please install the psycopg2 pypng python packages and libpg2-dev system package."
    sys.exit(1)

import settings
from operator import itemgetter


# import grass.script as grass
import gzip
import subprocess
from subprocess import Popen, PIPE, STDOUT
import shutil
import signal

import dbObj
import trim
import combine
from greencitieslog import log

    
def getBand(fname):
    """ Check which band is in a filename"""
    if 'b03.' in fname:
        return 3
    if 'b04.' in fname:
        return 4
    if 'b07.' in fname:
        return 7
    assert False


import gcswift


class BoundBox:
    """  """

    def __init__(self, box):
        self.xmin = box[0]
        self.ymin = box[1]
        self.xmax = box[2]
        self.ymax = box[3]

    def getBox(self):
        return [self.xmin, self.ymin, self.xmax, self.ymax]


import re

def checkValidImageSpec(identifierAsList):
    geomSpecOK = re.match("p[0-9][0-9][0-9]r[0-9][0-9][0-9]", identifierAsList[0])
    dateSpecOK = re.match("[5-7]dt[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]", identifierAsList[1])
    bandSpecOK = re.match("b[0-9][0-9]", identifierAsList[3])
    return geomSpecOK and dateSpecOK and bandSpecOK

def diagnoseBadSpec(identifierAsList, rawSpec):
    log("bad specifier: " + rawSpec)
    if len(identifierAsList) != 4:
        log("length of derived list must be 4, not " + len(identifierAsList))
        return
    geomSpecOK = re.match("p[0-9][0-9][0-9]r[0-9][0-9][0-9]", identifierAsList[0])
    dateSpecOK = re.match("[5-7]dt[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]", identifierAsList[1])
    bandSpecOK = re.match("b[0-9][0-9]", identifierAsList[3])
    if not geomSpecOK:
        log("bad geometry specifier " + identifierAsList[0])
    if not dateSpecOK:
        log("bad date specifier " + identifierAsList[1])
    if not bandSpecOK:
        log("bad band specifier " + identifierAsList[3])


#
# build an image identifier from a list of the form:
# "pnnnrnnn","ndtyyyymmdd","LL","b0n".  This expands to a filename of the
# form
# s = pieces[0]+"_"+pieces[1]+"."+pieces[2]+"."+pieces[3]+".tif.gz"
# caller has checked this...

import datetime

class imageID:
    def __init__(self, identifierAsList):
        geomSpec = identifierAsList[0]
        self.path = int(geomSpec[1:4])
        self.row = int(geomSpec[-3:])
        self.bucket = geomSpec
        dateSpec = identifierAsList[1]
        year = int(dateSpec[3:7])
        month = int(dateSpec[7:9])
        day = int(dateSpec[-2:])
        self.date = datetime.date(year, month, day)
        self.band = int(identifierAsList[3][-2:])
        self.fileName = "%s_%s.%s.%s.tif.gz" % tuple(identifierAsList)

    def subsumes(self, otherImageID):
        if self == otherImageID: return False
        if (self.bucket != otherImageID.bucket or self.band != otherImageID.band):
            return False
        return self.date > otherImageID.date

    def overlaps(self, otherImageID):
        if self.bucket == otherImageID.bucket: return False
        return (abs(self.path - otherImageID.path) <= 1) and (abs(self.row - otherImageID.row) <= 1)
    
                        
from operator import itemgetter, attrgetter        
        

class GrassLandsat:
    """ """

    def __init__(self, gid, cityName, box, coordSys, location):
        self.gid = gid
        self.city = cityName
        self.location = location
        if not self.city:
            self.city = ""

        self.bbox = BoundBox(box)
        self.projection = coordSys
        self.buckets = []
        self.files = []
        self.img = None
        self.havefiles = False


    def __del__(self):
        # this is where we should remove all the temp stuff
        toremove = os.path.join(os.environ['GISDBASE'], str(self.gid))+" "

        for (b, f) in self.buckets:
            toremove += "*"+b+"* "
        if self.img:
            toremove += self.img.fname+" "+self.img.imgname+" "
        toremove += str(self.gid)+"* "+"tmp2/"+str(self.gid)+"* "

        

    def check_bad_record(self, obj):
        """Does this record have the world wrap around bug? if so, discount"""
        b1 = obj['coordinates'][0][0]
        b2 = obj['coordinates'][0][1]
        b3 = obj['coordinates'][0][2]
        b4 = obj['coordinates'][0][3]
        
        leftlong = b1[0]
        rightlong = b3[0]
        
        #are we near the edge?
        if abs(leftlong) > 175 or abs(rightlong) > 175:
            isleftneg = leftlong<0
            isrightneg = rightlong<0
            if isleftneg != isrightneg:
                return True,[leftlong, rightlong]
            else:
                return False,[]
        else:
            return False,[]
            

        

    def getImgList(self,pgConn):
        """ """

        import json
        sql = "select fname, ST_AsGeoJson(tiff4326.the_geom) "\
            "from (select ST_Transform(the_geom, 4326) as the_geom from map where gid = "+str(self.gid)+") as map , tiff4326 where ST_Intersects(map.the_geom, tiff4326.the_geom);"

        records = pgConn.performSelect(sql)
        assert len(records), "No data crawled yet"

        decided_date = None

        self.images = []
        images = []
        for r in records:
            is_bad, bb = self.check_bad_record(json.loads(r[1]))
            if is_bad:
                log("Warning: Skipping " +  r[0] + " because of wraparound bug. Coords: " + str(bb))
                continue
            else:
                log("Info: Proccessing " + r[0])


            pieces = r[0].split('_')
            if len(pieces) == 4:
                # we only want 5dt or 7dt for landsat 7 (7),decade set (d) and triband (t)
                if 'dt' in pieces[1] and checkValidImageSpec(pieces):
                    images.append(imageID(pieces))
                else:
                    diagnoseBadSpec(pieces, r[0])

        # images1 = []

        for image in images:
            subsumed = reduce(lambda x,y: x or y, [otherImage.subsumes(image) for otherImage in images])
            if subsumed: continue
            self.images.append(image)
            # images1.append(image)


        # Make sure each image has a neighbor

        ## for image in images1:
        ##     hasNeighbor = reduce(lambda x, y: x or y, [otherImage.overlaps(image) for otherImage in images1])
        ##     if hasNeighbor: self.images.append(image)

        ## # If there are no connected images, just pick the one with the least path, least
        ## # row; any choice will do, we just need it to be consistent across bands

        ## if len(self.images) == 0:
        ##     images1 = sorted(images1, key=attrgetter('path', 'row'))
        ##     self.images = [images1[0]]
        
        

        # print "total images", len(images), "total unsubsumed images", len(images1), "total connected images", len(self.images)
        log("total images %s total subsumed images %s"%(len(images), len(self.images)))

        for image in self.images:
            self.files.append(image.fileName)
            self.buckets.append((image.bucket, image.fileName))
           

        
        log( "%s images intersect the city %s" % (len(self.files),self.city))

        return len(self.files)

    def checkImages(self):
        if len(self.images) == 0:
            log("No images for " + self.city)
            return
        if len(self.images) <= 3: return
        for image in self.images:
            hasNeighbor = reduce(lambda x, y: x or y, [otherImage.overlaps(image) for otherImage in self.images])
            if hasNeighbor: continue
            log("Isolated image for " + self.city)
            for myImage in self.images: log("(%d, %d)" % (myImage.path, myImage.row))
            return

    
    def getSwiftImgs(self):
        """ pull required buckets from swift into local dir """

        assert(len(self.files))
        assert(len(self.buckets))

        log("getting images from swift!")
        
        havebucket = False
        for b, f in self.buckets:
            if os.path.exists(f):
                log("Skipping file "+f+" as we already have it!")
                continue
            
            gcswift.swift("download", b, f)

        log("Complete!")
        self.havefiles = True


    # TODO: Stitch together all prefixes. Fk it, do it live
    def combineIntoPng(self):
        """ """

        

        def getMostRecentSet(fnames):
            """ """
            dates = []
            for f in fnames:
                # we are always encounter 'dt' before the date
                fdate = f.split('t')[1].split('.')[0]
                if fdate not in dates:
                    dates.append(int(fdate))

            maxdate = str(max(dates))
            newfiles = []
            for f in fnames:
                if maxdate in f:
                    newfiles.append(f)

            return newfiles


        def decompressTiffs(files):
            """ """
            tiffs = []
            cwd = os.getcwd()
            log("Decompressing files")
            try:
                for f in files:
                    tname = f.rstrip('.gz')
                    tiffs.append(tname)
                    if not os.path.exists(tname):
                        inf = gzip.GzipFile(os.path.join(cwd, f), 'rb')
                        dcmpdata = inf.read()
                        inf.close()
                        outf = open(tname, "w") # try catches????
                        outf.write(dcmpdata)
                        outf.close()
            except IOError as e:
                raise AssertionError(e)

            log("Complete!")
            return tiffs

        assert(self.havefiles)
        assert(len(self.files))

        # get raster 3 band images for each prefix
        fnames = decompressTiffs(self.files)
        #print fnames

        if len(fnames) > 3:
            log("Combining images")
            fnames = combine.combine_bands(fnames, str(self.gid))


        log("Getting shapefile for", str(self.gid))

        shpname = trim.getShapefile(self.gid)
        #try:
        trim.crop(shpname, fnames[0], fnames[1], fnames[2], prefix="trim_")
        fnames = ["trim_"+name for name in fnames]
        #except AssertionError as e:
        #    print e

        namesAndBands = [(fname, getBand(fname)) for fname in fnames]
        namesAndBands = sorted(namesAndBands, key=itemgetter(1), reverse=True)
        fnames = [fname for (fname, band) in namesAndBands]

        pre = str(self.gid)
        allbandsTIF = str(self.gid)+"_allbands.tif"
        allbandsPNG = str(self.gid)+"_allbands.png"

        mergeCmd = '/usr/local/bin/gdal_merge.py -n -9999 -a_nodata -9999 -separate  -o '

        mergeCmd += allbandsTIF

        for filename in fnames: mergeCmd += ' ' + filename

        log("creating... " + allbandsTIF +  " with "+ mergeCmd)

        p = Popen(mergeCmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        p.wait()
        output = p.stdout.read()
        assert p.returncode == 0, "Creation of merged bands Failed"
        log(output)

        #
        # Now convert to PNG
        #

        translateCmd = "/usr/local/bin/gdal_translate -of png -ot Byte -scale %s %s" % (allbandsTIF, allbandsPNG)
        log("creating... " +  allbandsPNG + " with " + translateCmd)

        p = Popen(translateCmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        p.wait()
        output = p.stdout.read()
        assert p.returncode == 0, "Creation of png  Failed"
        log(output)

        # we give it 1) the name of the png created from grass 
        #  and 2) the name the greenspace calc will create
        pngimg = pngImg(allbandsPNG, pre+".png")
        pngimg.bbox = self.bbox
        self.img = pngimg
            

    def uploadToSwift(self):
        log("Uploading processed image to swift")
        p = swift.do_swift_command(settings.SWIFT_PROXY, "upload", settings.SWIFT_PNG_BUCKET, False, self.img.imgname)
        assert p.returncode == 0, "Failed with %s"%(p.communicate()[1])
        log("Complete!")
        



class pngImg:
    fname = None
    imgname = None
    rgbs = None
    imgMeta = None
    px_w = None
    px_h = None
    bbox = None

    def __init__(self, fn, imgn):
        self.fname = fn
        self.imgname = imgn

    def readImgData(self):
        log("Attempting to read image data from " + self.fname)
        try:
            f = open(self.fname, 'rb')
            imgData = f.read()
            image = png.Reader(bytes=imgData)
            f.close()
            self.px_w, self.px_h, self.rgbs, self.metadata = image.asRGBA()
            self.rgbs = list(self.rgbs)
            log("Complete!")
        except IOError as e:
            print "Error:", str(e)
            raise AssertionError(str(e)) # crappy but this is all i catch atm

    def getXPerPixel(self):
        return (self.bbox.xmax - self.bbox.xmin) / self.px_w

    def getYPerPixel(self):
        return (self.bbox.ymax - self.bbox.ymin) / self.px_h

    def writeImg(self):
        log("Attemping to write png " + self.imgname)
        try:
            wt = png.Writer(width=self.px_w, height=self.px_h, alpha=True, bitdepth=8)
            f = open(self.imgname, 'wb')
            wt.write(f, self.rgbs)
            f.close()
            log("Complete!")
        except IOError as e:
            print "Error:", str(e)
            raise AssertionError(str(e))
