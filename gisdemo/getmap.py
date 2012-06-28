from owslib.wms import WebMapService
wms = WebMapService('http://ows.geobase.ca/wms/geobase_en', version='1.1.1')
print wms.identification.type
print wms.identification.version
print wms.identification.title
wms.identification.abstract
print list(wms.contents)


img = wms.getmap(   layers=['imagery:landsat7'],
                    styles=['visual_bright'],
                    srs='EPSG:4326',
                     bbox=(-112, 36, -106, 41),
                     size=(300, 250),
                     format='image/jpeg',
                     transparent=True
                     )
out = open('jpl_mosaic_visb.jpg', 'wb')
out.write(img.read())
out.close()
