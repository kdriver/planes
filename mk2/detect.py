"""  A program to detect planes and tweet """

import json
import time
import math
import os
import zipfile
import requests
import sqldb
import say



from vrs import Vrs
from loggit import loggit,init_loggit
from loggit import BOTH
from loggit import TO_SCREEN
# from loggit import TO_FILE
from loggit import GREEN_TEXT
from loggit import YELLOW_TEXT
from loggit import CYAN_TEXT
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
from my_queue import  INFINITE
from home import home
from blessed import Terminal

term = Terminal()
all_planes={}
# planes with closest approach to home of less that TWEET_RADIUS miles will be tweeted
TWEET_RADIUS=2.0

osm = requests.Session()
dump_planes = False
dump_icao = None
dump_time = 0

def get_term_width()->int:
    return term.width


def get_time(clock=time.time()):
    """ Return an ascii string of the current time """
    answer = time.asctime(time.localtime(clock))
    return answer


def enrich(icao_hex, the_plane):
    """ Given the icao hex for the plane, enrich the plane data from reference data """
    try:
        result = add_reference_data(icao_hex, the_plane)
    except Exception as my_exc:
        print(f"enrich exception {my_exp}")
        return
    # A tilde in the hex indicates a TIS-B record 
    # Dumping planes around the record gives a chance to see which plane it is
    if result is None and '~' not in icao_hex:
        loggit("could not enrich plane {}".format(icao_hex))
        return
    if result is None and '~' in icao_hex:
        # loggit("found tilde in icao , trigger a dump of planes around {}".format(icao))
        global dump_time, dump_icao, dump_planes
        dump_time = time.time() + 60
        dump_icao = icao_hex
        dump_planes = False
    the_plane['enriched'] = 1


def get_place(clat, clon):
    """ Use the Open Street Map API to look up the nearest place"""
    place = "unknown"
    try:
        req = "https://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}".format(
            clat, clon)
        resp = osm.get(url=req)
        pos = json.loads(resp.text)
        if 'display_name' in pos:
            place = pos['display_name']
        else:
            place = "somewhere"
    except Exception as e:
        loggit("could not access OSM API {} ".format(e))
        return None

    return place[0:90]
    
def nearest_point(the_plane):
    """ The plane has reached the nearest point to HOM, 
    so collect the report data, print it and insert it into the sql database
    Also write out the kml file with tracked path.
    and if its within TWEET_RADIUS - tweet it too """

    pd = "{} {}".format(get_time(the_plane["closest_time"]),the_plane['icao'])
    for item in ['icao_country','closest_miles','flight','tail','track','alt_baro','Owner','Manufacturer','plane','route']:
        if item in the_plane and the_plane[item] is not None:
            if item in {'closest_miles','track'}:
                pd = pd + " {:>7.2f} ".format(the_plane[item])
            elif  item in {'flight','tail','alt_baro'}:
                pd = pd + "{0:7} ".format(the_plane[item])
            elif item in { 'icao_country'}:
                pd = pd + f" {the_plane['icao_country']:<15}"
            else:
                pd = pd + " {:<} ".format(the_plane[item])
        else:
            if item in ['closest_miles','track','alt_baro']:
                the_plane[item] = 0
            else:
                the_plane[item] = "unknown"

    try:
        sqldb.insert_data((time.time(),the_plane["flight"],the_plane["icao"],the_plane["tail"],the_plane['plane'],the_plane["alt_baro"],the_plane["track"],the_plane["closest_miles"],the_plane["closest_lat"],the_plane["closest_lon"]))
    except Exception as e:
        loggit("could not insert data iinto planes record {}".format(e))

    name=''
    if 'tail' in the_plane:
        name=the_plane['tail']
    else:
        name='unknown'

    if 'alt_baro' not in the_plane:
        the_plane["alt_baro"] = "0"

    kml_text = kml_doc(the_plane['closest_lon'],the_plane['closest_lat'],  -1.9591988377888176,50.835736602072664, the_plane["alt_baro"],name,the_plane['closest_miles'],the_plane["tracks"])
    #redo_miles = Haversine()
    #with open("kmls/{}.kml".format(name),"w") as f:
    #    f.write(kml_text)
    #    f.close()
    with zipfile.ZipFile("kmls/{}.kmz".format(name),"w") as zf:
        zf.writestr("{}.kml".format(name),kml_text)
        zf.close()

    if 'expired' in the_plane:
        pd = pd + ' expired '

    linelen=145
    pd = pd[0:linelen]
    if len(pd) < 145:
        pd =  pd +" "*(linelen-len(pd))

    place = get_place(the_plane['closest_lat'],the_plane['closest_lon'])

    if place is None:
        place = " API failed "

    the_plane['reported'] = 1

    width = get_term_width()-1
    try:
        if 'miles' not in the_plane:
            pd = pd + " " + json.dumps(the_plane)
            loggit(pd,BOTH,CYAN_TEXT)
            return

        if the_plane['miles'] < TWEET_RADIUS:
            tweet(pd)
            pd = pd + " : " + place
            loggit(pd[:width],BOTH,GREEN_TEXT)
            txt = "the_plane overhead "
            if 'Owner' in the_plane:
                txt = txt + " " + the_plane['Owner']
            m = int(the_plane['miles'])

            if 'alt_baro' in the_plane:
                if the_plane['alt_baro'] != 'ground':
                    h = math.floor(int(the_plane['alt_baro'])/100)
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
            if 'plane' in the_plane:
                if 'DA42' in the_plane['plane']: 
                    loggit(pd[:width],BOTH,YELLOW_TEXT)
                else:
                    loggit(pd[:width],BOTH,CYAN_TEXT)
                    #loggit("{}".format(the_plane["tracks"].get_values()),BOTH,CYAN_TEXT)
    except Exception as e:
        loggit("reporting failed {}".format(e))



# Read the file produced by dump1090 and cache each the_plane seen so we can track its position reletive to home
# and check if it gets close.



def read_planes():
    """ read in the planes from dump1090 and cache the data """
    try:
        with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
            try:
                data = json.load(f)
            except Exception:
                print("error - can't open aircraft.json")

            global all_planes
            planes = data["aircraft"]
            #num_planes = len(planes)
            #print("num planes {}".format(num_planes))

            for plane in planes:
                start_miles = 1000
                miles = start_miles
                try:
                    icao = plane["hex"].strip().upper()
                    if icao not in all_planes:
                        all_planes[icao] = {"icao": icao, 'max_miles': 0.0, 'closest_miles': start_miles,
                                            'closest_lat': 0.0, 'closest_lon': 0.0, 'miles': start_miles, 'tracks': my_queue(INFINITE,icao)}
                    this_plane = all_planes[icao]
                    this_plane['touched'] = time.time()

                except Exception as e_name:
                    print(f"no icao  code in plane record {e_name} ")
                    continue

                for attr in ['lon', 'lat', 'flight', 'track', 'alt_baro']:
                    if attr in plane:
                        this_plane[attr] = plane[attr]

                if 'lat' in this_plane and 'lon' in this_plane and 'alt_baro' in this_plane:
                    try:
                        hv = Haversine(
                            home, [this_plane["lon"], this_plane["lat"]])
                        miles = hv.miles
                        bearing = int(hv.bearing)
                        this_plane['current_miles'] = miles
                        this_plane['tracks'].add(
                            {'miles': miles, "lon": this_plane["lon"], "lat": this_plane["lat"], "alt": this_plane["alt_baro"]})
                        if miles < this_plane['miles']:
                            this_plane['closest_lat'] = float(
                                this_plane['lat'])
                            this_plane['closest_lon'] = float(
                                this_plane['lon'])
                            this_plane['closest_alt'] = this_plane["alt_baro"]
                            this_plane['closest_miles'] = miles
                            this_plane["closest_time"] = time.time()
                            if this_plane['miles'] == start_miles:
                                #loggit("{:<7s} new plane  @ {:<7.2f} miles".format(icao,miles),TO_FILE)
                                pass
                            if 'reported' in this_plane:
                                del this_plane['reported']
                            this_plane['miles'] = miles
                        if miles > this_plane['max_miles']:
                            this_plane['max_miles'] = miles
                            this_plane['max_lon'] = this_plane['lon']
                            this_plane['max_lat'] = this_plane['lat']
                            if isinstance(this_plane["alt_baro"], int):
                                vrs.update_entry(
                                    bearing, this_plane["lat"], 
                                    this_plane["lon"], 
                                    this_plane["alt_baro"], 
                                    miles, 
                                    this_plane["icao"])

                    except Exception as e:
                        print("oh dear haversine {} {}".format(
                            e, json.dumps(this_plane)))
                        continue

                if miles < 200 and 'enriched' not in this_plane:
                    enrich(icao, this_plane)

                if (miles - this_plane['closest_miles']) > (this_plane['closest_miles']*0.1):
                    if 'reported' not in this_plane and this_plane['closest_miles'] < 50:
                        nearest_point(this_plane)
    except Exception as e_name:
        print(f" error in read_planes {e_name}\n")


def dump_the_planes(icao_hex):
    """Called to dump planes with similar height and distance"""
    loggit(f"Dump planes with similar distance to {icao_hex}")
    if icao_hex not in all_planes:
        loggit(f"could not find {icao_hex} in all_planes")
        return
    target = all_planes[icao_hex]

    if 'miles' not in target:
        loggit("could not find 'miles' in all_planes")
        return

    if 'lat' not in target or 'lon' not in target:
        loggit("target plane does not have both lat and lon - exit")
        return

    ll_target = [target['lat'], target['lon']]
    # distance = int(target['miles'])
    alt = int(target['alt_baro'])
    # loggit("Dump icao {} distance {}, {}".format(icao, distance, json.dumps(target, indent=4)))
    target_time = target['touched']
    for the_plane,_a_plane in all_planes.items():
        this_plane = all_planes[the_plane]
        proximity = 100
        if 'lat' in this_plane and 'lon' in this_plane:
            ll_this = [this_plane['lat'], this_plane['lon']]
            hv = Haversine(ll_target, ll_this)
            proximity = hv.miles

        h_diff = 1001
        if 'alt_baro' in this_plane and this_plane['alt_baro'] != 'ground':
            h_diff = abs(alt - int(this_plane['alt_baro']))

        if proximity < 20 and h_diff < 1000:
            txt = "{" + " hex:'{}',proximity:'{:.2f}'".format(icao, proximity)
            for item in ['icao', 'alt_baro', 'miles', 'track', 'tail', 'lat', 'lon']:
                if item in this_plane:
                    txt = txt + ",{}:'{}'".format(item, this_plane[item])
            txt = txt + ",version:'1'"
            txt = txt + ",tdiff:'{:.2f}', tn:'{}' ".format(
                (target_time - this_plane['touched']), get_time()) + "},"
            loggit(txt)


init_loggit("output.txt","/tmp/debug.txt")
init_reference_data()
update_reference_data()
start_webserver()
last_tick = time.time()
last_log = last_tick
sqldb.attach_sqldb()
vrs = Vrs("vrs_data.sqb")


while 1:
    read_planes()
    delete_list = []
    now = time.time()
    for icao,record in all_planes.items():
        if (now - record['touched']) > 60:
            delete_list.append(icao)

    for plane in delete_list:
        p = all_planes[plane]
        if 'reported' not in p and 'miles' in p and p['miles'] < 50:
            p['expired'] = 1
            nearest_point(p)
        write_kmz(home, p)
        del all_planes[plane]

    # check to see if we need to referesh any of the online databases
    update_reference_data()
    # update the cache used by the HTTP query to generate a table  ( default port 4443 )
    update_plane_data(all_planes)

    #triggered if we have seen a tilde encoded in the icao hex
    if dump_planes:
        if now > dump_time:
            dump_the_planes(dump_icao)
            dump_planes = False

    if os.path.exists("check_icao"):
        with open('check_icao') as f:
            s = f.read()
            dump_the_planes(str(s).strip().upper())
        os.remove('check_icao')

    # every 60 seconds
    if (now - last_tick) > 60:
        #   write out a kml file with all the t planes we can see
        three_d_vrs(all_planes)
        if (now - last_log) > 300:
            loggit("{} planes being tracked ".format(len(all_planes)), TO_SCREEN)
            last_log = now
        last_tick = now


    time.sleep(5)
