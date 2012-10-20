import os
import sys
try:
    import psycopg2
    import png
except:
    print "Error: Please install the psycopg2 pypng python packages and libpg2-dev system package."
    os.exit(1)

import settings


import grass.script as grass
import gzip
import subprocess
import shutil
import signal

import dbObj
import trim
import combine


# swift -A http://198.55.37.2:8080/auth/v1.0 -U system:gis -K uvicgis list completed
# so we dont hang trying to dl from swift

class Alarm(Exception):
    pass
def alarm_handler(signum, frame):
    raise Alarm


#signal.signal(signal.SIGALRM, alarm_handler)
#signal.alarm(5*60)  # 5 minutes
#stdoutdata, stderrdata = proc.communicate()
#signal.alarm(0)  # reset the alarm




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
    dateSpecOK = re.match("7dt[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]", identifierAsList[1])
    bandSpecOK = re.match("b[0-9][0-9]", identifierAsList[3])
    return geomSpecOK and dateSpecOK and bandSpecOK

def diagnoseBadSpec(identifierAsList, rawSpec):
    print "bad specifier:", rawSpec
    if len(identifierAsList) != 4:
        print "length of derived list must be 4, not", len(identifierAsList)
        return
    geomSpecOK = re.match("p[0-9][0-9][0-9]r[0-9][0-9][0-9]", identifierAsList[0])
    dateSpecOK = re.match("7dt[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]", identifierAsList[1])
    bandSpecOK = re.match("b[0-9][0-9]", identifierAsList[3])
    if not geomSpecOK:
        print "bad geometry specifier", identifierAsList[0]
    if not dateSpecOK:
        print "bad date specifier", identifierAsList[1]
    if not bandSpecOK:
        print "bad band specifier", identifierAsList[3]


#
# build an image identifier from a list of the form:
# "pnnnrnnn","7dtyyyymmdd","LL","b0n".  This expands to a filename of the
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

        ## print "rm -rf", toremove
        ## command = "rm -rf "+toremove
        ## p = subprocess.Popen(command, shell=True, 
        ##                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)


    def check_bad_record(self, obj):
        """Does this record have the world wrap around bug? if so, discount"""
        b1 = obj['coordinates'][0][0]
        b2 = obj['coordinates'][0][1]
        b3 = obj['coordinates'][0][2]
        b4 = obj['coordinates'][0][3]
        
        leftlat = b1[0]
        rightlat = b3[0]
        
        #are we near the edge?
        if abs(leftlat) > 175 or abs(rightlat) > 175:
            isleftneg = leftlat<0
            isrightneg = rightlat<0
            if isleftneg != isrightneg:
                return True,[leftlat, rightlat]
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
                print "Warning: Skipping", r[0], "because of wraparound bug. Coords:",bb
                continue
            else:
                print "Info: Proccessing", r[0]

            pieces = r[0].split('_')
            if len(pieces) == 4:
                # we only want 7dt for landsat 7 (7),decade set (d) and triband (t)

                # date = pieces[1][3:]
            #     if '7dt' in pieces[1]:
            #         # make sure dates line up
            #         if not decided_date:
            #             decided_date = date
            #         else:
            #             assert date == decided_date, "Adding images from two time peroids"

            #         s = pieces[0]+"_"+pieces[1]+"."+pieces[2]+"."+pieces[3]+".tif.gz"
            #         self.files.append(s)
            #         # if this is a new prefix add it to the bucket list so we can dl from swift
            #         if pieces[0] not in self.buckets:
            #             self.buckets.append(pieces[0])
            #     else:
            #         print "Skipping", r[0]
            # else:
            #     raise Exception("Invalid image name in database:" + r[0])

                if '7dt' in pieces[1] and checkValidImageSpec(pieces):
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
        print "total images", len(images), "total unsubsumed images",  len(self.images)

        for image in self.images:
            self.files.append(image.fileName)
            self.buckets.append((image.bucket, image.fileName))
           

        ## s = pieces[0]+"_"+pieces[1]+"."+pieces[2]+"."+pieces[3]+".tif.gz"
        ##             self.files.append(s)
        ##             # if this is a new prefix add it to the bucket list so we can dl from swift
        ##             if pieces[0] not in self.buckets:
        ##                 self.buckets.append(pieces[0])

        # assert(len(self.files)) == 3, "Currently can't stitch together images, skipping " + str(self.gid)
        print len(self.files), "images intersect the city", self.city

        return len(self.files)

    def checkImages(self):
        if len(self.images) == 0:
            print "No images for", self.city
            return
        if len(self.images) <= 3: return
        for image in self.images:
            hasNeighbor = reduce(lambda x, y: x or y, [otherImage.overlaps(image) for otherImage in self.images])
            if hasNeighbor: continue
            print "Isolated image for", self.city
            for myImage in self.images: print myImage.path, myImage.row
            return

    
    def getSwiftImgs(self):
        """ pull required buckets from swift into local dir """

        assert(len(self.files))
        assert(len(self.buckets))

        print "getting images from swift!"

        ## for b in self.buckets:
        ##     havebucket = 0
        ##     for f in self.files:
        ##         if b in f:
        ##             if os.path.exists(f):
        ##                 print "Skipping bucket "+b+" as we already have it!"
        ##                 havebucket = 1
        ##     if not havebucket:

        ##         command = "swift -A "+settings.SWIFT_PROXY+" -U "+settings.SWIFT_USER+" -K "+settings.SWIFT_PWD+" download "+b
        ##         # spawna shell that executes swift, we set the sid of the shell so
        ##         #  we can kill it and all its children with os.killpg
        ##         p = subprocess.Popen(command, shell=True, 
        ##                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ##                              preexec_fn=os.setsid) 

        ##         try:
        ##             signal.signal(signal.SIGALRM, alarm_handler)
        ##             signal.alarm(3*60)  # we will timeout after 3 minutes 

        ##             p.wait()
        ##             signal.alarm(0)  # reset the alarm
        ##         except Alarm:
        ##             os.killpg(p.pid, signal.SIGTERM)
        ##             # raise an assertion so we can continue execution after 
        ##             #  (should really have our own exception but fk it)
        ##             raise AssertionError("Timeout gettimg images from swift")

        ##         assert p.returncode == 0, "Failed with %s"%(p.communicate()[1])

        ## print "Complete!"
        ## self.havefiles = 1

        
        havebucket = False
        for (b, f) in self.buckets:
            if os.path.exists(f):
                print "Skipping file "+f+" as we already have it!"
                continue
            

            command = "swift -A "+settings.SWIFT_PROXY+" -U "+settings.SWIFT_USER+" -K "+settings.SWIFT_PWD+" download "+b+ " " + f
            # spawna shell that executes swift, we set the sid of the shell so
            #  we can kill it and all its children with os.killpg
            p = subprocess.Popen(command, shell=True, 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 preexec_fn=os.setsid) 

            try:
                signal.signal(signal.SIGALRM, alarm_handler)
                signal.alarm(3*60)  # we will timeout after 3 minutes 

                p.wait()
                signal.alarm(0)  # reset the alarm
            except Alarm:
                os.killpg(p.pid, signal.SIGTERM)
                # raise an assertion so we can continue execution after 
                #  (should really have our own exception but fk it)
                raise AssertionError("Timeout gettimg images from swift")

            assert p.returncode == 0, "Failed with %s"%(p.communicate()[1])

        print "Complete!"
        self.havefiles = True


    # TODO: Stitch together all prefixes. Fk it, do it live
    def combineIntoPng(self):
        """ """

        def getBand(fname):
            """ Check which band is in a filename"""
            if 'b03.' in fname:
                return 3
            if 'b04.' in fname:
                return 4
            if 'b07.' in fname:
                return 7
            assert False

        def getMostRecentSet(fnames):
            """ """
            dates = []
            for f in fnames:
                # we are always encounter '7dt' before the date
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
            print "Decompressing files"
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

            print "Complete!"
            return tiffs

        assert(self.havefiles)
        assert(len(self.files))

        # get raster 3 band images for each prefix
        fnames = decompressTiffs(self.files)
        #print fnames

        if len(fnames) > 3:

            print "Combining images"
            fnames = combine.combine_bands(fnames, str(self.gid))

            # need this to reproject later!
            nproj = trim.get_projection(fnames[0])

            # for each bucket we combine 3 bands and normalize the colour
            for (b, old_f) in self.buckets:
                l = []
                for f in fnames:
                    if b in f:
                        l.append(f)
                
                #print l

                assert len(l) == 3, "Bucket has to many images to combine"
                pre = b
                outtiffs = []
            
                # p = grass.run_command("r.in.gdal", input=l[0], 
                #                       output=pre+"."+str(getBand(fnames[0])), location=pre)

                # p = grass.run_command("g.mapset", location=pre, mapset="PERMANENT")
                # for f in l[1:]:
                #     p = grass.run_command("r.in.gdal", input=f, 
                #                           output=pre+"."+str(getBand(f)) )       

                # # equalize colour values, eg. min green = min blue etc
                # p = grass.run_command("i.landsat.rgb", red=pre+".7",
                #                       green=pre+".4", blue=pre+".3")

                # # combine bands into one image
                # p = grass.run_command("r.composite", red=pre+".7", green=pre+".4",
                #                       blue=pre+".3", output=pre+".rgb")

                outtiff = b+"tmp_grass.png.tif"
                outtiffs.append(outtiff)
                # p = grass.run_command("r.out.tiff", input=pre+".rgb", output=outtiff)

                # # reset the map so we dont fail creating a location
                # p = grass.run_command("g.mapset", location="landsat7", mapset="PERMANENT")     

            # print "Combining images"
            # fnames = combine.combine_single(outtiffs, str(self.gid))

            # assert len(fnames) == 1

            # print "Getting shapefile for", str(self.gid)
            # shpname = trim.getShapefile(self.gid)
            # #try:
            # trim.crop(shpname, fnames[0], prefix="trim_", new_projcode=nproj)
            # fnames = ["trim_"+name for name in fnames]
            # #except AssertionError as e:
            # #    print e

            # #This is a crappy way to convert to a png! But oh well
            # pre = str(self.gid)
            # p = grass.run_command("r.in.gdal", input=fnames[0], 
            #                       output=pre+"."+str(getBand(fnames[0])), location=pre)
            # outpng = str(self.gid)+"_grass.png"
            # p = grass.run_command("r.out.png", input=pre+".rgb", output=outpng)


        #else:

        log("Getting shapefile for", str(self.gid))
        shpname = trim.getShapefile(self.gid)
        #try:
        trim.crop(shpname, fnames[0], fnames[1], fnames[2], prefix="trim_")
        fnames = ["trim_"+name for name in fnames]
        #except AssertionError as e:
        #    print e

        pre = str(self.gid)

        #read images into grass
        p = grass.run_command("r.in.gdal", input=fnames[0], 
                              output=pre+"."+str(getBand(fnames[0])), location=pre)
        p = grass.run_command("g.mapset", location=pre, mapset="PERMANENT")
        for f in fnames[1:]:
            p = grass.run_command("r.in.gdal", input=f, 
                                  output=pre+"."+str(getBand(f)) )       

        # equalize colour values, eg. min green = min blue etc
        p = grass.run_command("i.landsat.rgb", red=pre+".7",
                              green=pre+".4", blue=pre+".3")

        # combine bands into one image
        p = grass.run_command("r.composite", red=pre+".7", green=pre+".4",
                              blue=pre+".3", output=pre+".rgb")

        outpng = str(self.gid)+"_grass.png"
        p = grass.run_command("r.out.png", input=pre+".rgb", output=outpng)

        # reset the map so we dont fail creating a location
        p = grass.run_command("g.mapset", location="landsat7", mapset="PERMANENT")

        # we give it 1) the name of the png created from grass 
        #  and 2) the name the greenspace calc will create
        pngimg = pngImg(outpng, pre+".png")
        pngimg.bbox = self.bbox
        self.img = pngimg
            

    def uploadToSwift(self):
        print "Uploading processed image to swift"
        command = "swift -A "+settings.SWIFT_PROXY+" -U "+settings.SWIFT_USER+" -K "\
            +settings.SWIFT_PWD+" upload "+settings.SWIFT_PNG_BUCKET+" "+self.img.imgname
        p = subprocess.Popen(command, shell=True, 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        assert p.returncode == 0, "Failed with %s"%(p.communicate()[1])
        print "Complete!"
        



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
        print "Attempting to read image data from", self.fname
        try:
            f = open(self.fname, 'rb')
            imgData = f.read()
            image = png.Reader(bytes=imgData)
            f.close()
            self.px_w, self.px_h, self.rgbs, self.metadata = image.asRGBA()
            self.rgbs = list(self.rgbs)
            print "Complete!"
        except IOError as e:
            print "Error:", str(e)
            raise AssertionError(str(e)) # crappy but this is all i catch atm

    def getXPerPixel(self):
        return (self.bbox.xmax - self.bbox.xmin) / self.px_w

    def getYPerPixel(self):
        return (self.bbox.ymax - self.bbox.ymin) / self.px_h

    def writeImg(self):
        print "Attemping to write png", self.imgname
        try:
            wt = png.Writer(width=self.px_w, height=self.px_h, alpha=True, bitdepth=8)
            f = open(self.imgname, 'wb')
            wt.write(f, self.rgbs)
            f.close()
            print "Complete!"
        except IOError as e:
            print "Error:", str(e)
            raise AssertionError(str(e))
