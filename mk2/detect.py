import json
import time
from loggit import loggit
from loggit import BOTH as BOTH
from loggit import GREEN_TEXT as GREEN_TEXT
from loggit import RED_TEXT as RED_TEXT
from  Haversine import Haversine
from reference_data import update_reference_data
from reference_data import init_reference_data
from reference_data import add_reference_data
from twitter import tweet

global the_time

home=[-1.95917,50.83583]
all_planes={}
TWEET_RADIUS=2.0


def get_time():
    answer = time.asctime(time.localtime(time.time()))
    return answer

the_time = get_time()

def enrich(icoa,plane):
    add_reference_data(icoa,plane)
    plane['enriched'] = 1

def nearest_point(plane):
    pd = "-> nearest   {} ".format(plane['icoa'])
    for item in ['miles','flight','tail','track','alt_baro','Owner','Manufacturer','plane','route']:
        if item in plane:
            if item in {'miles','track'}:
                pd = pd + " {:<7.2f} ".format(plane[item])
            else:
                pd = pd + " {} ".format(plane[item])

#    if 'miles' in plane:
#        pd = pd + " {: <2.2f} ".format(plane['miles'])
#    if 'flight' in plane:
#        pd = pd + " {} ".format(plane['flight'])
#    if 'tail' in plane:
#        pd = pd + " {} ".format(plane['tail'])
#    if 'plane' in plane:
#        pd = pd + " {} ".format(plane['plane'])
#    if 'track' in plane:
#        pd = pd + " {: <3.2f} ".format(plane['track'])
#    if 'alt_baro' in plane:
#        pd = pd + " {} ".format(plane['alt_baro'])
#    if 'route' in plane:
#        pd = pd + " {} ".format(plane['route'])
    plane['reported'] = 1
    if plane['miles'] < TWEET_RADIUS:
        loggit(pd,BOTH,GREEN_TEXT)
        tweet(pd)
    else:
        loggit(pd,BOTH)

def read_planes():
    with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
        try:
            data = json.load(f)
        except:
            print("error - can't open aircraft.json")

        time_now = data["now"]
        messages = data["messages"]
        planes   = data["aircraft"]
        num_planes = len(planes)
        #print("num planes {}".format(num_planes))

        for plane in planes:
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

            try:
                miles = Haversine([this_plane["lon"],this_plane["lat"]],home).nm
            except Exception as e:
                #print("oh dear {} {}".format(e,json.dumps(this_plane)))
                continue

            if miles < 50:
                if 'enriched' not in this_plane:
                    enrich(icoa,this_plane)
#                print("plane {} {: <02.2f} {}".format(icoa,miles,this_plane))

                if 'miles' in this_plane:
                    #print("plane {} now {}  previous {} {}".format(icoa,miles,this_plane['miles'],miles < this_plane['miles']))
                    if miles < this_plane['miles']:
                        this_plane['miles'] = miles
                        if 'reported' in this_plane:
                            loggit("{} re approching".format(icoa),BOTH)
                            del this_plane['reported']
                    else:
                        if (miles - this_plane['miles']) > (this_plane['miles']*0.1):
                            if 'reported' not in this_plane:
                                nearest_point(this_plane)
                else:
                    loggit("{:<7s} new plane  @ {:<7.2f} miles".format(icoa,miles),BOTH)
                    this_plane['miles'] = miles

                #print("->this plane {}".format(this_plane))

    
init_reference_data()
update_reference_data()

while 1:
    read_planes()
    time.sleep(5)
    delete_list = []
    for icoa in all_planes:
        now = time.time()
        if (now - all_planes[icoa]['touched']) > 60:
            delete_list.append(icoa)

    for plane in delete_list:
        del all_planes[plane]
       # print("delete {}".format(plane))
