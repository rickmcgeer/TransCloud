from owslib.wms import WebMapService
import png
box = (-123.57411,48.3106147, -123.20006,48.6980295)
wms = WebMapService('http://ows.geobase.ca/wms/geobase_en', version='1.1.1')
print wms.identification.type
print wms.identification.version
print wms.identification.title
wms.identification.abstract
print list(wms.contents)
print wms['imagery:landsat7'].styles

img = wms.getmap(   layers=['imagery:landsat7'],
                    styles=[],
                    srs='EPSG:4326',
                     bbox=box,
                     size=(300, 250),
                     format='image/png',
                     transparent=True
                     )

bytes_of_png = img.read()


image = png.Reader(bytes=bytes_of_png)

rgbs = list(image.asRGBA()[2])
pixels = 0
rs = 0
bs = 0
gs = 0
for row in rgbs:
    for pixel in row[0::4]:
        pixels += 1
        if pixel > 128:
            rs += 1
    for pixel in row[1::4]:
        pixels += 1
        if pixel > 128:
            gs += 1
    for pixel in row[2::4]:
        pixels += 1
        if pixel > 128:
            bs += 1


print pixels, rs, bs, gs
