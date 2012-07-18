from owslib.wms import WebMapService
import png


# dict for worldwide wms servers
WMS_SERVER = {'canada':"http://ows.geobase.ca/wms/geobase_en", 'us':"http://198.55.37.8:8080/geoserver/opengeo/wms"}
WMS_LAYER = {'canada':['imagery:landsat7'], 'us':[['Landsat7:L7-US-70-UTM11N'],[''],['']]}

IMG_LOC = "/tmp/"

class landsatImg:
    """  """

    gid = None
    city = None
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


    def writeImg(self):
        try:
            wt = png.Writer(width=self.w, height=self.h, alpha=True, bitdepth=8)
            f = open(IMG_LOC+self.city+str(self.gid), 'wb')
            wt.write(f, self.rgbs)
            f.close()
        except IOError as e:
            #log(e)
            print "Error:", str(e)



class bandedLandsatImg(landsatImg):
    """  """

    def getImg(self):
        None
        
    def getImgData(self):
        None
