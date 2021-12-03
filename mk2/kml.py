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
      cline = "{},{},{}".format(track["lon"],track["lat"],alt)
      coords = coords + cline +  "\n"

    return text.format(name,dist,lon1,lat1,lon2,lat2,coords)


if __name__ == "__main__":
    home=[ -1.9591988377888176,50.835736602072664]
    p1 = [-2.0079,50.814423]
    with open("test.kml","w") as f:
        f.write(kml_doc(home[0],home[1],p1[0],p1[1],'tflight',15.6))
