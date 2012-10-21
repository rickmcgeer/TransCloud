from owslib.wms import WebMapService
import png
import settings

# dict for worldwide wms servers
WMS_SERVER = {'canada':"http://ows.geobase.ca/wms/geobase_en", 'us':"http://localhost:8080/geoserver/Landsat7/wms"}
WMS_LAYER = {'canada':['imagery:landsat7'], 'us':[['L7-US-70'],['L7-US-40'],['L7-US-30']]}

IMG_LOC = settings.TEMP_FILE_DIR + "/"
IMG_EXT = ".png"

class landsatImg:
    """  """

    gid = None
    city = None
    location = None
    bbox = None
    w = None
    h = None
    server = None
    layer = None
    wms = None
    img = None
    px_w = None
    px_h = None
    rgbs = None
    imgMeta = None

    class boundBox:
        """  """

        def __init__(self, box):
            self.xmin = box[0]
            self.ymin = box[1]
            self.xmax = box[2]
            self.ymax = box[3]

        def getBox(self):
            return [self.xmin, self.ymin, self.xmax, self.ymax]


    def __init__(self, gid, cityName, box, coordSys, width, height, location):
        self.gid = gid
        self.city = cityName
        self.location = location
        if not self.city:
            self.city = ""

        self.bbox = self.boundBox(box)
        self.projection = coordSys
        self.w = width
        self.h = height
        self.server = WMS_SERVER[location]
        self.layer = WMS_LAYER[location]
        self.wms = self.getWms()
        self.img = self.getImg()
        self.px_w, self.px_h, self.rgbs, self.imgMeta = self.getImgData()
        

    def getWms(self):
        return WebMapService(self.server, version='1.1.1')


    def getImg(self):
        return self.wms.getmap(layers=self.layer,
                               styles=[],
                               srs=self.projection,
                               bbox=self.bbox.getBox(),
                               size=(self.w, self.h),
                               format='image/png',
                               transparent=True)


    def getImgData(self):
        imgData = self.img.read()
        image = png.Reader(bytes=imgData)
        px_wid, px_hei, rgbs, metadata = image.asRGBA()
        return px_wid, px_hei, list(rgbs), metadata

    
    def getXPerPixel(self):
        return (self.bbox.xmax - self.bbox.xmin) / self.px_w
    

    def getYPerPixel(self):
        return (self.bbox.ymax - self.bbox.ymin) / self.px_h

    def getImgName(self):
        return self.city+str(self.gid)+IMG_EXT

    def writeImg(self):
        try:
            wt = png.Writer(width=self.w, height=self.h, alpha=True, bitdepth=8)
            f = open(IMG_LOC+self.getImgName(), 'wb')
            wt.write(f, self.rgbs)
            f.close()
        except IOError as e:
            #log(e)
            print "Error:", str(e)




class bandedLandsatImg(landsatImg):
    """  """


    def getImg(self):
        """  """

        if len(self.layer) != 3:
            print "banded image without 3 layers!"
            return # we should raise some sort of error

        def getBand(self, layer):
            """  """
            return self.wms.getmap(layers=layer,
                                   styles=[],
                                   srs=self.projection,
                                   bbox=self.bbox.getBox(),
                                   size=(self.w, self.h),
                                   format='image/png',
                                   transparent=True)

        red = self.getBand(self.layer[0])
        green = self.getBand(self.layer[1])		
        blue = self.getBand(self.layer[2])

        return [red, green, blue]



    def getImgData(self):
        """  """

        if len(self.img) != 3:
            print "banded image without 3 bands!"
            return # raise some sort of error

        def getPixels(self, img):
            """  """
            imgBytes = img.read()
            image = png.Reader(bytes=imgBytes)
            return image.asRGBA()

        px_wid, px_hei, rgbs, metadata = self.getPixels(img[0])
        green = list(self.getPixels(img[1])[2])
        blue = list(self.getPixels(img[2])[2])

        rgbs = list(rgbs)	
        i=0
        while i<len(rgbs):
            j=0
            while j<len(rgbs[i]):
                rgbs[i][j+1] = greens[i][j+1]
                rgbs[i][j+2] = blues[i][j+2]
                j+=4
            i+=1	
	
        return px_wid, px_hei, rgbs, metadata
