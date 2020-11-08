import json
import time
import copy
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
from loggit import RED_TEXT as RED_TEXT
from Haversine import Haversine
from reference_data import update_reference_data
from reference_data import init_reference_data
from reference_data import add_reference_data
from twitter import tweet
from http.server import HTTPServer,BaseHTTPRequestHandler
from web import start_webserver
from web import update_plane_data

home=[-1.95917,50.83583]
all_planes={}
TWEET_RADIUS=2.0

osm = requests.Session()
dump_planes = False
dump_icoa = None
dump_time = 0

def planes_table():
    page = "<th>"


def get_time():
    answer = time.asctime(time.localtime(time.time()))
    return answer

def enrich(icoa,plane):
    result  = add_reference_data(icoa,plane)
     # if there is a tilde in the icoa and we could not resolve it, then in 60 seconds dump the planes
    if result == None and '~' in icoa:
        global dump_time,dump_icoa,dump_planes
        dump_time = time.time() + 60
        dump_icoa = icoa
        dump_planes = True
    plane['enriched'] = 1

def nearest_point(plane):
    pd = "{} -> nearest   {} ".format(get_time(),plane['icoa'])
    for item in ['closest_miles','flight','tail','track','alt_baro','Owner','Manufacturer','plane','route']:
        if item in plane:
            if item in {'closest_miles','track'}:
                pd = pd + " {:>7.2f} ".format(plane[item])
            else:
                pd = pd + " {} ".format(plane[item])

    try:
        req = "https://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}".format(plane['closest_lat'],plane['closest_lon'])
        #print(req)
        resp = osm.get(url=req)
        pos = json.loads(resp.text)
        place="unknown"
        if 'display_name' in pos:
                place = pos['display_name']
        else:
                place = "somewhere"
    except Exception as e:
        loggit("could not access OSM API {} ".format(e))
            
    try:
        sqldb.insert_data((time.time(),plane["flight"],plane["icoa"],plane["tail"],plane['plane'],plane["alt_baro"],plane["track"],plane["closest_miles"],plane["closest_lat"],plane["closest_lon"]))
    except:
        pass

    plane['reported'] = 1
    if 'expired' in plane:
        pd = pd + ' expired '
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
                h = math.floor(int(plane['alt_baro'])/100)
                if h > 9:
                    txt = txt + " at " + str(h/10) + " thousand feet"
                else:
                    txt = txt + " at " + str(h) + " hundred feet"

            txt = txt + " distance {:>1.1f} miles".format(m)
            say.speak(txt)
        else:
            if 'plane' in plane:
                if 'DA42' in plane['plane']: 
                    loggit(pd,BOTH,YELLOW_TEXT)
                else:
                    loggit(pd,BOTH)
    else:
        pd = pd + " " + json.dumps(plane)
        loggit(pd,BOTH)

def read_planes():
    with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
        try:
            data = json.load(f)
        except:
            print("error - can't open aircraft.json")

        global all_planes
        time_now = data["now"]
        messages = data["messages"]
        planes   = data["aircraft"]
        num_planes = len(planes)
        #print("num planes {}".format(num_planes))

        for plane in planes:
            start_miles = 1000
            miles = start_miles
            try:
                icoa = plane["hex"].strip().upper()
                if icoa not in all_planes:
                    all_planes[icoa] = { "icoa" : icoa , 'closest_miles' : start_miles,'closest_lat' : 0.0 , 'closest_lon' : 0.0 , 'miles' : start_miles }
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
                    miles = Haversine([this_plane["lon"],this_plane["lat"]],home).nm
                    this_plane['current_miles'] = miles
                    if miles < this_plane['miles']:
                        this_plane['closest_lat'] = float(this_plane['lat'])
                        this_plane['closest_lon'] = float(this_plane['lon'])
                        this_plane['closest_miles'] = miles
                        if this_plane['miles'] == start_miles:
                            loggit("{:<7s} new plane  @ {:<7.2f} miles".format(icoa,miles),TO_FILE)
                        if 'reported' in this_plane:
                            del this_plane['reported']
                        this_plane['miles'] = miles

                except Exception as e:
                    print("oh dear haversine {} {}".format(e,json.dumps(this_plane)))
                    continue

            #if miles < 50:
            if  miles < 200 and 'enriched' not in this_plane:
                enrich(icoa,this_plane)
#                print("plane {} {: <02.2f} {}".format(icoa,miles,this_plane))

                #print("plane {} now {}  previous {} {}".format(icoa,miles,this_plane['miles'],miles < this_plane['miles']))
            if (miles - this_plane['closest_miles']) > (this_plane['closest_miles']*0.1):
                if 'reported' not in this_plane and this_plane['miles'] < 50:
                    nearest_point(this_plane)

init_reference_data()
update_reference_data()
start_webserver()
last_tick = 0
sqldb.attach_sqldb()

def dump_planes(icoa):
        loggit("Dump planes with similar distance to {}".format(icoa))
        if icoa in all_planes:
            target = all_planes[icoa]
            if 'miles' in target:
                distance = int(target['miles'])
                loggit("Dump ICOA {} , {}".format(icoa,json.dumps(target,indent=4)))
                for plane in all_planes:
                        this_plane = all_planes[plane]
                        if abs(this_plane['miles'] - distance) < 10:
                                txt = ""
                                for item in ['icoa','track','tail','miles','alt_baro','lat','lon']:
                                        if item in this_plane:
                                                txt = txt + " {}:{}".format(item,this_plane[item])
                                
                                loggit(txt)
            else:
                loggit("could not find 'miles' in all_planes")
                pass
        else:
            loggit("could not find {} in all_planes".format(icoa))
            pass

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
       # print("delete {}".format(plane))
    update_reference_data() 
    update_plane_data(all_planes)
    if dump_planes == True:
        if now > dump_time:
                dump_planes(dump_icoa)
                dump_planes = False

    if os.path.isfile("check_icoa"):
        with open('check_icoa') as f: 
                s = f.read()
                dump_planes(str(s).strip().upper())
                os.remove('check_icoa')

    if ( now - last_tick ) >  60*60*1000 :
        loggit("{} planes being tracked ".format(len(all_planes)))
        last_tick = now
    time.sleep(5)

