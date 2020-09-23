import json
import time
import copy
import sqldb
from loggit import loggit
from loggit import BOTH as BOTH
from loggit import TO_FILE as TO_FILE
from loggit import GREEN_TEXT as GREEN_TEXT
from loggit import YELLOW_TEXT as YELLOW_TEXT
from loggit import RED_TEXT as RED_TEXT
from  Haversine import Haversine
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

def planes_table():
    page = "<th>"


def get_time():
    answer = time.asctime(time.localtime(time.time()))
    return answer

def enrich(icoa,plane):
    add_reference_data(icoa,plane)
    plane['enriched'] = 1

def nearest_point(plane):
    pd = "{} -> nearest   {} ".format(get_time(),plane['icoa'])
    for item in ['miles','flight','tail','track','alt_baro','Owner','Manufacturer','plane','route']:
        if item in plane:
            if item in {'miles','track'}:
                pd = pd + " {:>7.2f} ".format(plane[item])
            else:
                pd = pd + " {} ".format(plane[item])

    try:
        sqldb.insert_data((time.time(),plane["flight"],plane["icoa"],plane["tail"],plane['plane'],plane["alt_baro"],plane["track"],plane["miles"],plane["lat"],plane["lon"]))
    except:
        pass

    plane['reported'] = 1
    if 'expired' in plane:
        pd = pd + ' expired '
    if 'miles' in plane:
        if plane['miles'] < TWEET_RADIUS:
            loggit(pd,BOTH,GREEN_TEXT)
            tweet(pd)
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
            miles = 1000
            try:
                icoa = plane["hex"].strip().upper()
                if icoa not in all_planes:
                    all_planes[icoa] = { "icoa" : icoa }
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
                except Exception as e:
                    print("oh dear haversine {} {}".format(e,json.dumps(this_plane)))
                    continue

            #if miles < 50:
            if  miles < 200 and 'enriched' not in this_plane:
                enrich(icoa,this_plane)
#                print("plane {} {: <02.2f} {}".format(icoa,miles,this_plane))

            if 'miles' in this_plane:
                #print("plane {} now {}  previous {} {}".format(icoa,miles,this_plane['miles'],miles < this_plane['miles']))
                if miles < this_plane['miles']:
                    this_plane['miles'] = miles
                    if 'reported' in this_plane:
                        #loggit("{} re approching".format(icoa),BOTH)
                        del this_plane['reported']
                else:
                    if (miles - this_plane['miles']) > (this_plane['miles']*0.1):
                        if 'reported' not in this_plane and this_plane['miles'] < 50:
                            nearest_point(this_plane)
            else:
                loggit("{:<7s} new plane  @ {:<7.2f} miles".format(icoa,miles),TO_FILE)
                this_plane['miles'] = miles

                #print("->this plane {}".format(this_plane))

init_reference_data()
update_reference_data()
start_webserver()
last_tick = 0
sqldb.attach_sqldb()

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
    if ( now - last_tick ) >  60*60*1000 :
        loggit("{} planes being tracked ".format(len(all_planes)))
        last_tick = now
    time.sleep(5)

