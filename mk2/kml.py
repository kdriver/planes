import zipfile
from my_queue import my_queue
from loggit import loggit
from home import home

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

splat_text = """<?xml version='1.0' encoding='UTF-8'?>
<kml xmlns:ns="http://earth.google.com/kml/2.0">
  <Folder>
    <Style id="kdd">
      <LineStyle>
        <color>ff00f0ff</color>
        <width>2</width>
      </LineStyle>
    </Style>
    <Style id="YGP">
      <LineStyle>
      <color>{}</color>
      <width>4</width>
      </LineStyle>
      <PolyStyle>
      <color>{}</color>
      </PolyStyle>
    </Style>

    <Placemark>
    <styleUrl>#YGP</styleUrl>
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

vrs_text = """
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
{}
</Document>
</kml>
"""
# <href>http://maps.google.com/mapfiles/kml/pushpin/blue-pushpin.png</href>
placemark_text = """
<Placemark>
<Style><IconStyle><Icon>
  <heading>{}</heading>
  <href>http://maps.google.com/mapfiles/kml/shapes/airports.png</href>
</Icon></IconStyle></Style>
<name> {} </name>
<Point>
   <extrude>1</extrude>
   <altitudeMode>absolute</altitudeMode>
   <coordinates>
   {}
   </coordinates>
</Point>
</Placemark>
"""

red='7f0000ff'

def kml_doc(lon1,lat1,lon2,lat2,alt,name,dist,tracks):
    coords = ""
    for track in tracks.get_values():
      cline = "{},{},{}".format(track["lon"],track["lat"],track["alt"])
      coords = coords + cline +  "\n"

    return text.format(name,dist,lon1,lat1,lon2,lat2,coords)

def splat_doc(radar_points,name,line_col,face_col):
    coords = ""
    for point in radar_points:
      cline = "{},{},{}".format(point[1],point[0],point[2])
      coords = coords + cline +"\n"
    
    doc_text = splat_text.format(line_col,face_col, coords)
    zf = zipfile.ZipFile("splat_{}.kmz".format(name),"w")
    zf.writestr("{}.kml".format(name),doc_text)
    zf.close()

def three_d_vrs(all_planes):
  placemarks = ""
  for plane in all_planes:
    this_plane = all_planes[plane]
    proceed = True
    for txt in ['miles','lat','lon','alt_baro','tail','track']:
      if txt not in this_plane:
        proceed = False

    if proceed is True:
      if this_plane['miles'] : # < 180:
        coords = "{},{},{}".format(this_plane['lon'],this_plane['lat'],this_plane['alt_baro'])
        the_text = this_plane['tail'] + " | " + this_plane['icao']
        placemark = placemark_text.format(this_plane['track'],the_text,coords)
        placemarks = placemarks + placemark 
    # else:
    #  print("False {}".format(this_plane['icao']))

  doc_text = vrs_text.format(placemarks)  
  zf = zipfile.ZipFile("vrs.kmz","w")
  zf.writestr("vrs.kml",doc_text)
  zf.close()



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


