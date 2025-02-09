import sqlite3
import datetime
from kml import splat_doc
red = '7f0000ff'
green = '7f00ff00'
blue = '7fff0000'
db  = sqlite3.connect("vrs_data.sqb")
cur = db.cursor()
coords_max = []
for deg in range(0,359,1):
    answer = cur.execute("SELECT lat_max,lon_max,alt_max,miles_max FROM Vrs WHERE bearing = {};".format(deg))
    txt = answer.fetchone()
    if txt is not None and txt[0] != 0.0:
        coords_max= coords_max + [txt]

splat_doc(coords_max,"max",red,red)

coords_10k = []
for deg in range(0,359,1):
    answer = cur.execute("SELECT lat_10k,lon_10k,alt_10k,miles_10k FROM Vrs WHERE bearing = {};".format(deg))
    txt = answer.fetchone()
    if txt is not None and txt[0] != 0.0:
        coords_10k = coords_10k + [txt]

splat_doc(coords_10k,"10k",blue,blue)

coords_20k = []
for deg in range(0,359,1):
    answer = cur.execute("SELECT lat_20k,lon_20k,alt_20k,miles_20k FROM Vrs WHERE bearing = {};".format(deg))
    txt = answer.fetchone()
    if txt is not None and txt[0] != 0.0:
        coords_20k = coords_20k + [txt]

splat_doc(coords_20k,"20k",green,green)

print(datetime.datetime.now())



