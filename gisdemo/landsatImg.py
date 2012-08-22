import psycopg2
import grass.script as grass
import gzip
import os
import subprocess
import png

import dbObj
import trim

SWIFT_PROXY = "http://198.55.37.2:8080/auth/v1.0"
SWIFT_USER = "system:gis"
SWIFT_PWD = "uvicgis"
SWIFT_PNG_BUCKET = "completed"

IMG_LOC = "/tmp/"
IMG_EXT = ".png"


class boundBox:
    """  """

    def __init__(self, box):
        self.xmin = box[0]
        self.ymin = box[1]
        self.xmax = box[2]
        self.ymax = box[3]

    def getBox(self):
        return [self.xmin, self.ymin, self.xmax, self.ymax]


class grasslandsat:
    """ """

    gid = None
    city = None
    location = None
    projection = None
    bbox = None
    buckets = []
    files = []
    imgs = []
    havefiles = 0


    def __init__(self, gid, cityName, box, coordSys, location):
        self.gid = gid
        self.city = cityName
        self.location = location
        if not self.city:
            self.city = ""

        self.bbox = boundBox(box)
        self.projection = coordSys


    def __del__(self):
        # this is where we should remove all the temp stuff
        toremove = ""

        for b in self.buckets:
            toremove += b+"* "+os.path.join(os.environ['GISBASE'],b)+" "
        for img in self.imgs:
            toremove += img.fname+" "+img.imgname

        subprocess.call(["rm", "-rf", toremove])


    def getImgList(self, wkt):

        dbConn = dbObj()
        sql = "select fname from (select gid, ST_ConvexHull(the_geom) as the_geom from map where gid = "+str(self.gid)+") as M, tiff where ST_Intersects(M.the_geom, tiff.the_geom);"
        # Given box query GIS database, get list of buckets back as well as their coords!
        records = dbObj.performSelect(sql)

        self.files = ["p110r023_5dt20060717.SR.b03.tif.gz",
                      "p110r023_5dt20060717.SR.b04.tif.gz",
                      "p110r023_5dt20060717.SR.b07.tif.gz"]
        

    def getSwiftImgs(self):
        """ pull required buckets from swift into local dir """

        if not len(self.files):
            print "No files to get for swift"
            return

        # get all the buckets we need
        for f in self.files:
            fpre = f.split('_')[0]
            if fpre not in self.buckets:
                self.buckets.append(fpre)
# TESTING COMMENT OUT
        # for b in self.buckets:
        #     subprocesS.Check_call(["swift", "-A", SWIFT_PROXY, "-U", SWIFT_USER,
        #                           "-K", SWIFT_PWD, "download", b])
       
        self.havefiles = 1


    # TODO: Stitch together all prefixes. Fk it, do it live
    def combineIntoPng(self):
        """ """

        def getBand(fname):
            """ """
            if '.b03.' in fname:
                return 3
            if '.b04.' in fname:
                return 4
            if '.b07.' in fname:
                return 7


        def getMostRecentSet(fnames):
            """ """
            dates = []
            for f in fnames:
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

            for f in files:
                inf = gzip.GzipFile(os.path.join(cwd, f), 'rb')
                dcmpdata = inf.read()
                inf.close()
                tname = f.rstrip('.gz')
                outf = open(tname, "w") # try catches????
                tiffs.append(tname)
                outf.write(dcmpdata)
                outf.close()

            return tiffs

        if not self.havefiles:
            print "We must get files from swift first!"
            return

        if not len(self.files):
            print "No images to combine!"
            return

        # get prefixes for all the tiles
        prefixes = self.buckets

        # sort files by their prefixes
        sortfiles = {}
        for pre in prefixes:
            sortfiles[pre] = []
            for f in self.files:
                if pre in f:
                    sortfiles[pre].append(f)

        # get raster 3 band images for each prefix
        for pre in sortfiles:

            fnames = sortfiles[pre]
            if len(fnames) > 3:
                # we will use only the most recent date set if we have more than 1
                fnames = getMostRecentSet(fnames)

            fnames = decompressTiffs(fnames)    
            
            print "Getting shapefile for", str(self.gid)

            shpname = trim.getShapefile(self.gid)
            try:
                trim.crop(shpname, fnames[0], fnames[1], fnames[2], prefix="new_")
                fnames = ["new_"+name for name in fnames]
            except AssertionError as e:
                print e

            # read images into grass
            grass.run_command("r.in.gdal", input=fnames[0], 
                              output=pre+"."+str(getBand(fnames[0])), location=pre)
            grass.run_command("g.mapset", location=pre, mapset="PERMANENT")
            for f in fnames[1:]:
                grass.run_command("r.in.gdal", input=f, 
                                  output=pre+"."+str(getBand(f)) )       

            # equalize colour values, eg. min green = min blue etc
            grass.run_command("i.landsat.rgb", red=pre+".7", 
                                  green=pre+".4", blue=pre+".3")

            # combine bands into one image
            grass.run_command("r.composite", red=pre+".7", green=pre+".4",
                                  blue=pre+".3", output=pre+".rgb")

            grass.run_command("r.out.png", input=pre+".rgb", output=pre+".png")

            grass.run_command("g.mapset", location="landsat7", mapset="PERMANENT")
            
            pngimg = pngImg(pre+".png")

# DANGER!!!!
            pngimg.bbox = self.bbox

            self.imgs.append(pngimg)
            

    def uploadToSwift(self):
        imgnames = ""
        for img in self.imgs:
            imgnames += str(img.imgname) + " "

        imgnames = imgnames.strip()
        subprocess.check_call(["swift", "-A", SWIFT_PROXY, "-U", SWIFT_USER, 
                               "-K", SWIFT_PWD, "upload", SWIFT_PNG_BUCKET, imgnames])



class pngImg:
    fname = None
    imgname = "default.png"
    rgbs = None
    imgMeta = None
    #w = None
    #h = None
    px_w = None
    px_h = None
    bbox = None

    def __init__(self, name):
        self.fname = name

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
