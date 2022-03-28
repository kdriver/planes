import json
import time
import sqldb
import say
import math
import requests
import os
from vrs import Vrs
from loggit import loggit
from loggit import BOTH as BOTH
from loggit import TO_FILE as TO_FILE
from loggit import GREEN_TEXT as GREEN_TEXT
from loggit import YELLOW_TEXT as YELLOW_TEXT
from loggit import CYAN_TEXT as CYAN_TEXT
#from loggit import RED_TEXT as RED_TEXT
from Haversine import Haversine
from reference_data import update_reference_data
from reference_data import init_reference_data
from reference_data import add_reference_data
from twitter import tweet
from web import start_webserver
from web import update_plane_data
from kml import kml_doc
from kml import write_kmz
from kml import three_d_vrs
from my_queue import my_queue
from my_queue import  INFINATE as INFINATE
import zipfile
from home import home


all_planes={}
# planes with closest approach to home of less that TWEET_RADIUS miles will be tweeted
TWEET_RADIUS=2.0

osm = requests.Session()
dump_planes = False
dump_icoa = None
dump_time = 0


def get_time(clock=time.time()):
    answer = time.asctime(time.localtime(clock))
    return answer

def enrich(icoa,plane):
    result  = add_reference_data(icoa,plane)
    # if there is a tilde in the icoa and we could not resolve it, then in 60 seconds dump the planes
    if result is None:
        loggit("could not enrich plane")
    if result is None and '~' in icoa:
        loggit("found tilde in icoa , trigger a dump of planes around {}".format(icoa))
        global dump_time,dump_icoa,dump_planes
        dump_time = time.time() + 60
        dump_icoa = icoa
        dump_planes = True
    plane['enriched'] = 1

def get_place(clat,clon):
    place = "unknown"
    try:
        req = "https://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}".format(clat,clon)
        resp = osm.get(url=req)
        pos = json.loads(resp.text)
        if 'display_name' in pos:
            place = pos['display_name']
        else:
            place = "somewhere"
    except Exception as e:
        loggit("could not access OSM API {} ".format(e))

    return place[0:90]
            
    
def nearest_point(plane):
    pd = "{} -> nearest   {} ".format(get_time(plane["closest_time"]),plane['icoa'])
    for item in ['closest_miles','flight','tail','track','alt_baro','Owner','Manufacturer','plane','route']:
        if item in plane:
            if item in {'closest_miles','track'}:
                pd = pd + " {:>7.2f} ".format(plane[item])
            elif  item in {'flight','tail','alt_baro'}:
                pd = pd + "{0:7} ".format(plane[item])
            else:
                pd = pd + " {:<} ".format(plane[item])
    try:
        sqldb.insert_data((time.time(),plane["flight"],plane["icoa"],plane["tail"],plane['plane'],plane["alt_baro"],plane["track"],plane["closest_miles"],plane["closest_lat"],plane["closest_lon"]))
    except:
        pass

    name=''
    if 'tail' in plane:
        name=plane['tail']
    else:
        name='unknown'

    if 'alt_baro' not in plane:
        plane["alt_baro"] = "0"

    kml_text = kml_doc(plane['closest_lon'],plane['closest_lat'],  -1.9591988377888176,50.835736602072664, plane["alt_baro"],name,plane['closest_miles'],plane["tracks"])
    #redo_miles = Haversine()
    #with open("kmls/{}.kml".format(name),"w") as f:
    #    f.write(kml_text)
    #    f.close()
    with zipfile.ZipFile("kmls/{}.kmz".format(name),"w") as zf:
        zf.writestr("{}.kml".format(name),kml_text)
        zf.close()

    if 'expired' in plane:
        pd = pd + ' expired '

    linelen=145
    pd = pd[0:linelen]
    if len(pd) < 145:
        pd =  pd +" "*(linelen-len(pd))

    place = get_place(plane['closest_lat'],plane['closest_lon'])

    plane['reported'] = 1

    if 'miles' in plane:
        if plane['miles'] < TWEET_RADIUS:
            tweet(pd)
            pd = pd + " : " + place
            loggit(pd,BOTH,GREEN_TEXT)
            txt = "plane overhead "
            if 'Owner' in plane:
                txt = txt + " " + plane['Owner']
            m = int(plane['miles'])

            if 'alt_baro' in plane:
                if plane['alt_baro'] != 'ground':
                    h = math.floor(int(plane['alt_baro'])/100)
                    if h > 9:
                        txt = txt + " at " + str(h/10) + " thousand feet"
                    else:
                        txt = txt + " at " + str(h) + " hundred feet"
            else:
                txt = txt + " on ground"

            txt = txt + " distance {:>1.1f} miles".format(m)
            say.speak(txt)
        else:
            pd = pd + " : " + place
            if 'plane' in plane:
                if 'DA42' in plane['plane']: 
                    loggit(pd,BOTH,YELLOW_TEXT)
                else:
                    loggit(pd,BOTH,CYAN_TEXT)
                    #loggit("{}".format(plane["tracks"].get_values()),BOTH,CYAN_TEXT)
    else:
        pd = pd + " " + json.dumps(plane)
        loggit(pd,BOTH,CYAN_TEXT)
        #loggit("{}".format(plane["tracks"].get_values()),BOTH,CYAN_TEXT)

"""
Read the file produced by dump1090 and cache each plane seen so we can track its position reletive to home
and check if it gets close.
"""
def read_planes():
        try:
            with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
                try:
                    data = json.load(f)
                except:
                    print("error - can't open aircraft.json")

                global all_planes
                planes   = data["aircraft"]
                #num_planes = len(planes)
                #print("num planes {}".format(num_planes))

                for plane in planes:
                    start_miles = 1000
                    miles = start_miles
                    try:
                        icoa = plane["hex"].strip().upper()
                        if icoa not in all_planes:
                            all_planes[icoa] = { "icoa" : icoa , 'max_miles' : 0.0 , 'closest_miles' : start_miles,'closest_lat' : 0.0 , 'closest_lon' : 0.0 , 'miles' : start_miles , 'tracks' : my_queue(INFINATE)}
                        this_plane = all_planes[icoa]
                        this_plane['touched'] = time.time()
                    
                    except Exception as e:
                        print("no icoa  code in plane record {} ".format(e))
                        continue

                    for  attr in ['lon','lat','flight','track','alt_baro']:
                        if attr in plane:
                            this_plane[attr] = plane[attr]

                    if 'lat' in this_plane and 'lon' in this_plane and 'alt_baro' in this_plane:
                        try:
                            hv = Haversine(home,[this_plane["lon"],this_plane["lat"]])
                            miles = hv.miles
                            bearing = int(hv.bearing)
                            this_plane['current_miles'] = miles
                            this_plane['tracks'].add({'miles':miles,"lon":this_plane["lon"],"lat":this_plane["lat"],"alt":this_plane["alt_baro"]})
                            if miles < this_plane['miles']:
                                this_plane['closest_lat'] = float(this_plane['lat'])
                                this_plane['closest_lon'] = float(this_plane['lon'])
                                this_plane['closest_alt'] = this_plane["alt_baro"]
                                this_plane['closest_miles'] = miles
                                this_plane["closest_time"] = time.time()
                                if this_plane['miles'] == start_miles:
                                    #loggit("{:<7s} new plane  @ {:<7.2f} miles".format(icoa,miles),TO_FILE)
                                    pass
                                if 'reported' in this_plane:
                                    del this_plane['reported']
                                this_plane['miles'] = miles
                            if miles > this_plane['max_miles']:
                                this_plane['max_miles'] = miles
                                this_plane['max_lon']   = this_plane['lon']
                                this_plane['max_lat']   = this_plane['lat'] 
                                if isinstance(this_plane["alt_baro"],int):
                                    vrs.update_entry(bearing,this_plane["lat"],this_plane["lon"],this_plane["alt_baro"],miles,this_plane["icoa"])

                        except Exception as e:
                            print("oh dear haversine {} {}".format(e,json.dumps(this_plane)))
                            continue

                    if  miles < 200 and 'enriched' not in this_plane:
                        enrich(icoa,this_plane)

                    if (miles - this_plane['closest_miles']) > (this_plane['closest_miles']*0.1):
                        if 'reported' not in this_plane and this_plane['closest_miles'] < 50:
                            nearest_point(this_plane)
        except Exception as e:
                print(" error in read_planes {}\n".format(e))




def dump_the_planes(icoa):
    loggit("Dump planes with similar distance to {}".format(icoa))
    if icoa in all_planes:
        target = all_planes[icoa]
        if 'miles' in target:

            if 'lat' not in target or  'lon' not in target:
                loggit("target plane does not have both lat and lon - exit")
                return

            ll_target = [target['lat'],target['lon']]
            distance = int(target['miles'])
            alt = int(target['alt_baro'])
            loggit("Dump ICOA {} distance {}, {}".format(icoa,distance, json.dumps(target,indent=4)))
            target_time = target['touched']
            for plane in all_planes:
                this_plane = all_planes[plane]
                proximity = 100
                if 'lat' in this_plane and 'lon' in this_plane:
                    ll_this = [ this_plane['lat'],this_plane['lon']]
                    hv = Haversine(ll_target,ll_this)
                    proximity = hv.miles

                hd=1001
                if 'alt_baro' in this_plane and this_plane['alt_baro'] != 'ground':
                    hd = abs(alt - int(this_plane['alt_baro']))

                if proximity < 20 and hd < 1000:
                    txt = "{" + " hex:{},proximity:{:.2f}".format(icoa,proximity)
                    for item in ['icoa','alt_baro','miles','track','tail','lat','lon']:
                        if item in this_plane:
                            txt = txt + ",{}:{}".format(item,this_plane[item])

                    txt = txt + ",tdiff:{:.2f}, tn:'{}' ".format((target_time - this_plane['touched']),get_time()) + "},"
                    loggit(txt)
        else:
            loggit("could not find 'miles' in all_planes")
    else:
        loggit("could not find {} in all_planes".format(icoa))


init_reference_data()
update_reference_data()
start_webserver()
last_tick = time.time()
sqldb.attach_sqldb()
vrs = Vrs("vrs_data.sqb")


while 1:
    read_planes()
    delete_list = []
    now = time.time()
    for icoa in all_planes:
        if (now - all_planes[icoa]['touched']) > 60:
            delete_list.append(icoa)

    for plane in delete_list:
        p = all_planes[plane]
        if  'reported' not in p and 'miles' in p and p['miles'] < 50 :
            p['expired'] = 1
            nearest_point(p)
        write_kmz(home,p)
        del all_planes[plane]

    # check to see if we need to referesh any of the online databases
    update_reference_data() 
    # update the cache used by the HTTP query to generate a table  ( default port 4443 )
    update_plane_data(all_planes)

    #triggered if we have seen a tilde encoded in the icoa hex
    if dump_planes:
        if now > dump_time:
            dump_the_planes(dump_icoa)
            dump_planes = False

    if os.path.exists("check_icoa"):
        with open('check_icoa') as f: 
            s = f.read()
            dump_the_planes(str(s).strip().upper())
        os.remove('check_icoa')

    # every 60 seconds
    if ( now - last_tick ) >  60 :
        loggit("{} planes being tracked ".format(len(all_planes)))
        last_tick = now
        #   write out a kml file with all the t planes we can see
        three_d_vrs(all_planes)
    
    time.sleep(5)
