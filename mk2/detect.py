import json
import time
import sqldb
import say
import math
import requests
import os
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
from my_queue import my_queue

# lon , lat
home=[-1.95917,50.83583]
all_planes={}
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
    kml_text = kml_doc(plane['closest_lon'],plane['closest_lat'],  -1.9591988377888176,50.835736602072664, plane["alt_baro"],name,plane['closest_miles'],plane["tracks"])
    #redo_miles = Haversine()
    with open("kmls/{}.kml".format(name),"w") as f:
        f.write(kml_text)
        f.close()

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
                            all_planes[icoa] = { "icoa" : icoa , 'closest_miles' : start_miles,'closest_lat' : 0.0 , 'closest_lon' : 0.0 , 'miles' : start_miles , 'tracks' : my_queue(50)}
                        this_plane = all_planes[icoa]
                        this_plane['touched'] = time.time()
                    
                    except Exception as e:
                        print("no icoa icao code in plane record {} ".format(e))
                        continue

                    for  attr in ['lon','lat','flight','track','alt_baro']:
                        if attr in plane:
                            this_plane[attr] = plane[attr]

                    if 'lat' in this_plane and 'lon' in this_plane:
                        try:
                            miles = Haversine([this_plane["lon"],this_plane["lat"]],home).miles
                            this_plane['current_miles'] = miles
                            this_plane['tracks'].add({'miles':miles,"lon":this_plane["lon"],"lat":this_plane["lat"]})
                            if miles < this_plane['miles']:
                                this_plane['closest_lat'] = float(this_plane['lat'])
                                this_plane['closest_lon'] = float(this_plane['lon'])
                                this_plane['closest_miles'] = miles
                                this_plane["closest_time"] = time.time()
                                if this_plane['miles'] == start_miles:
                                    loggit("{:<7s} new plane  @ {:<7.2f} miles".format(icoa,miles),TO_FILE)
                                if 'reported' in this_plane:
                                    del this_plane['reported']
                                this_plane['miles'] = miles

                        except Exception as e:
                            print("oh dear haversine {} {}".format(e,json.dumps(this_plane)))
                            continue

                    if  miles < 200 and 'enriched' not in this_plane:
                        enrich(icoa,this_plane)

                    if (miles - this_plane['closest_miles']) > (this_plane['closest_miles']*0.1):
                        if 'reported' not in this_plane and this_plane['miles'] < 50:
                            nearest_point(this_plane)
        except Exception as e:
                print(" error in read_planes {}\n".format(e))


init_reference_data()
update_reference_data()
start_webserver()
last_tick = 0
sqldb.attach_sqldb()

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
                    proximity = Haversine(ll_target,ll_this).miles

                hd=1001
                if 'alt_baro' in this_plane and this_plane['alt_baro'] != 'ground':
                    hd = abs(alt - int(this_plane['alt_baro']))

                if proximity < 20 and hd < 1000:
                    txt = " {}: proximity : {:.2f} ".format(icoa,proximity)
                    for item in ['icoa','alt_baro','miles','track','tail','lat','lon']:
                        if item in this_plane:
                            txt = txt + " {}:{}".format(item,this_plane[item])

                    txt = txt + " tdiff = {:.2f} tn = {}".format((target_time - this_plane['touched']),get_time())
                    loggit(txt)
        else:
            loggit("could not find 'miles' in all_planes")
    else:
        loggit("could not find {} in all_planes".format(icoa))


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
        del all_planes[plane]
        #print("delete {}".format(plane))
    update_reference_data() 
    update_plane_data(all_planes)
    if dump_planes:
        if now > dump_time:
            dump_the_planes(dump_icoa)
            dump_planes = False

    if os.path.exists("check_icoa"):
        with open('check_icoa') as f: 
            s = f.read()
            dump_the_planes(str(s).strip().upper())
        os.remove('check_icoa')

    if ( now - last_tick ) >  60*60*1000 :
        loggit("{} planes being tracked ".format(len(all_planes)))
        last_tick = now
    time.sleep(5)
