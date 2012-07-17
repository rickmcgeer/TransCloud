from owslib.wms import webMapService
import png


# dict for worldwide wms servers
WMS_SERVER = {'canada':"http://ows.geobase.ca/wms/geobase_en", 'us':"http://198.55.37.8:8080/geoserver/opengeo/wms"}
WMS_LAYER = {'canada':['imagery:landsat7'], 'us':[['Landsat7:L7-US-70-UTM11N'],[''],['']]}


class landsatImg:
    """  """

    def __init__(self, gid, cityName="", bbox, coordSys, width, height, location):
        self.gid = gid
        self.city = cityName
        self.bbox = bbox
        self.projection = coordSys
        self.w = width
        self.h = height
        self.server = WMS_SERVER[location]
        self.layer = WMS_LAYER[location]
        self.wms = self.getWms()
        self.img = self.getImg()
        self.px_w, self.px_h, self.rgbs, self.imgData = self.getImageData()
        

    def getWms(self):
        return WebMapService(self.server, version='1.1.1')


    def getImg(self)
        return self.wms.getmap(layers=self.layer,
                               styles=[],
                               srs=self.projection,
                               bbox=self.bbox,
                               size=(self.w, self.h),
                               format='image/png',
                               transparent=True)


    def getImgData(self):
        imgData = self.img.read()
        image = png.Reader(bytes=imgData)
        px_wid, px_hei, rgbs, metadata = image.asRGBA()
        return px_wid, px_hei, list(rgbs), metadata


    def writeImg():
        None



class bandedLandsatImg(landsatImg):
    """  """

    def getImg(self):
        None
        
    def getImgData(self):
        None
