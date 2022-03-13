import zipfile
from my_queue import my_queue
from loggit import loggit

text = """<?xml version='1.0' encoding='UTF-8'?>
<kml xmlns:ns="http://earth.google.com/kml/2.0">
  <Folder>
    <Style id="kdd">
      <LineStyle>
        <color>ff0000ff</color>
        <width>2</width>
      </LineStyle>
    </Style>
  <Placemark>
        <name>{}</name>
      <description> miles={}</description>
      <styleUrl>#kdd</styleUrl>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <coordinates>{},{},0  {},{},0</coordinates>
      </LineString>
    </Placemark>
    <Placemark>

    <LineString>
    <extrude>1</extrude>
    <tessellate>1</tessellate>
    <altitudeMode>absolute</altitudeMode>
    <coordinates>
    {}
    </coordinates>
    </LineString>
    </Placemark>
  </Folder>
</kml>
"""

def kml_doc(lon1,lat1,lon2,lat2,alt,name,dist,tracks):
    coords = ""
    for track in tracks.get_values():
      cline = "{},{},{}".format(track["lon"],track["lat"],track["alt"])
      coords = coords + cline +  "\n"

    return text.format(name,dist,lon1,lat1,lon2,lat2,coords)
  
def write_kmz(h,p):
  if 'tail' in p and 'closest_miles' in p and 'reported' in p:
    name = p['tail']
    if p['closest_miles'] < 50:
      doc = kml_doc(h[0],h[1],p['closest_lon'],p['closest_lat'],p['closest_alt'],p['tail'],p['closest_miles'],p['tracks'])
      # loggit("write {}_f.kmz".format(name))
      zf = zipfile.ZipFile("kmls/{}_f.kmz".format(name),"w")
      zf.writestr("{}.kml".format(name),doc)
      zf.close()
  


if __name__ == "__main__":
    home=[ -1.9591988377888176,50.835736602072664]
    p1 = [-2.00790,50.814423]
    tracks = my_queue(500)
    tlon = home[0]
    tlat = home[1]
    for point in range(0,10,1):
      tlon = tlon + 0.1
      tlat = tlat + 0.1
      track = { 'lon':tlon,'lat':tlat,'alt':1000}
      tracks.add(track)


    doc = kml_doc(home[0],home[1],p1[0],p1[1],15000,'tflight',15.6,tracks)

    with open("test.kml","w") as f:
        f.write(doc)
    zf = zipfile.ZipFile("test.kmz","w")
    zf.writestr("loc.kml",doc)
    zf.close()


