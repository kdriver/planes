import json
import time
import pprint
import math
import requests
import os
import pprint
import sqlite3

from birdy.twitter import UserClient
import twittertokens

client = UserClient(twittertokens.CONSUMER_KEY,twittertokens.CONSUMER_SECRET,
                    twittertokens.ACCESS_TOKEN,twittertokens.ACCESS_TOKEN_SECRET)

try:
        conn = sqlite3.connect('StandingData.sqb')
        print("connected")
except Exception as e: 
	print (e)
	exit()

import signal

def handler(signum,stack):
        print("caught it")

signal.signal(signal.SIGUSR1,handler)

#orgurl='https://ae.roplan.es/api/callsign-origin_IATA.php?callsign='
orgurl="https://ae.roplan.es/api/callsign-origin_IATA.php?callsign="
desturl='https://ae.roplan.es/api/callsign-des_IATA.php?callsign='
plane_url='https://ae.roplan.es/api/hex-type.php?hex='
reg_url='https://ae.roplan.es/api/hex-reg.php?hex='

global api_requests
api_requests=0

log = open("monitor.txt","a")
log.write("New session %s \n" % ((time.asctime( time.localtime(time.time())))))
log.flush()

def degrees_to_cardinal(x):
    '''
    note: this is highly approximate...
    '''

    d = float(x)
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = int((d + 11.25)/22.5)
    return dirs[ix % 16]

class Haversine:
    '''
    use the haversine class to calculate the distance between
    two lon/lat coordnate pairs.
    output distance available in kilometers, meters, miles, and feet.
    example usage: Haversine([lon1,lat1],[lon2,lat2]).feet

    '''
    def __init__(self,coord1,coord2):
        lon1,lat1=coord1
        lon2,lat2=coord2

        R=6371000                               # radius of Earth in meters
        phi_1=math.radians(lat1)
        phi_2=math.radians(lat2)

        delta_phi=math.radians(lat2-lat1)
        delta_lambda=math.radians(lon2-lon1)

        a=math.sin(delta_phi/2.0)**2+\
           math.cos(phi_1)*math.cos(phi_2)*\
           math.sin(delta_lambda/2.0)**2
        c=2*math.atan2(math.sqrt(a),math.sqrt(1-a))

        self.meters=R*c                         # output distance in meters
        self.km=self.meters/1000.0              # output distance in kilometers
        self.miles=self.meters*0.000621371      # output distance in miles
        self.feet=self.miles*5280               # output distance in feet
        self.nm=self.miles/1.15               # output distance in feet

me=[-1.95917,50.83583]

def get_reg(flight):
	url=reg_url+flight
	url=url.strip()
	response=requests.post(url)
	return response.text
	
def get_plane(flight):
	url=plane_url+flight
	url=url.strip()
	response=requests.post(url)
	return response.text
	
def get_route(flight):
	global conn
	answer = conn.execute("SELECT FromAirportName,ToAirportName  FROM RouteView WHERE Callsign = '%s'" % flight.strip() )
	txt = answer.fetchone()
	if txt  != None:
		route = "%s -> %s" % txt
		return route

	furl=orgurl+flight
	furl=furl.strip()
	turl=desturl+flight
	turl=turl.strip()
	rfrom = ''
	rto = ''
	global api_requests
	try :
		fresponse = requests.post(furl)
		rfrom = fresponse.text
		api_requests+=1
		tresponse = requests.post(turl)
		api_requests+=1
		rto = tresponse.text

		route = rfrom + " -> " + rto
	except Exception as e: print("oh no", e)

	return route


current_planes =  dict()

def read_planes() :
	with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
		try:
			data = json.load(f)
		except:
			return


	planes = data["aircraft"]

#	t = time.time()
#	x = t/86400  + 25569
#	d = int(t) % 86400
#	pp = pprint.PrettyPrinter()
#pp.pprint(planes)

	this_plane = {}

	global api_requests
	global log
	api_requests = 0 
#	print(" planes in list %d" % (len(planes)))

	touched =0
	for plane in planes:
		try:
			hex = plane["hex"]
			try:
				this_plane = current_planes[hex]
			except:
				current_planes[hex] = { "hex" : hex }
				this_plane = current_planes[hex]

			try:
				this_plane["lon"] = plane["lon"]
			except:
				pass
			try:
				this_plane["lat"] = plane["lat"]
			except:
				pass

			try:
				this_plane["flight"] = plane["flight"]
			except:
				pass

			try:
				this_plane["altitude"] = plane["alt_baro"]
			except:
				pass

			try:
				this_plane["track"] = plane["track"]
			except:
				pass


                        try: 
                                miles = Haversine([this_plane["lon"],this_plane["lat"]],me).nm
                                if miles < 25: 
                                        try:
                                                route = this_plane["plane"]
                                        except:
                                                response = get_plane(this_plane["hex"])
                                                if response != '':
                                                        this_plane["plane"]=response
                                        try:
                                                reg = this_plane["reg"]
                                        except:
                                                response = get_reg(this_plane["hex"])
                                                if response != '':
                                                        this_plane["reg"]=response

                                        try:
                                                 route = this_plane["route"]
                                        except:
                                                response = get_route(this_plane["flight"])
                                                if response != '':
                                                        this_plane["route"]=response
                                        try:
                                                old_miles = this_plane["miles"]
                                        except:
                                                this_plane["miles"] = miles

                                        if miles <= this_plane["miles"]:
                                                this_plane["miles"] = miles
                                                try:
                                                        del this_plane["done"]
                                                except:
                                                        pass
                                        else:
                                                try:
                                                        pdone = this_plane["done"]
                                                except:
                                                        this_plane["done"]=1
                                                        pd = "%s %s %s %s %s %s track %s  alt=%s nearest point %8.2f " % (time.asctime( time.localtime(time.time()) ),this_plane["flight"],this_plane["hex"],this_plane["reg"], this_plane["plane"],this_plane["route"],this_plane["track"],this_plane["altitude"],this_plane["miles"])
                                                        if this_plane["miles"] < 2.0:
                                                                print("TWEET :")
                                                                log.write("TWEET   : ")
                                                                try:
                                                                        response = client.api.statuses.update.post(status=pd)
                                                                except Exception as e: print(e)

                                                        print(pd)
                                                        log.write("%s \n" % (pd) )
                                                        log.flush()
                        except:
                                pass

			this_plane["touched"] = time.time()
			touched+=1
			current_planes[hex] = this_plane
				
                except  :
                    pass
#                Exception as e: print("> %s " % e)

#as e: print(">",e,plane)

#os.system('clear')

while 1:
	read_planes()
	global api_requests
	time.sleep(10)
#	print("-------- %d %d" % (api_requests,len(current_planes)))
	now = time.time()
	touched=0

	four=0
	delete_list = []
	for plane_hex in current_planes:
		try:
			plane = current_planes[plane_hex]
			last_time = plane["touched"]
			td = now - last_time

			if  td  > 60.0:
				delete_list.append( plane_hex )
			touched+=1
		except :
			pass

	for plane in delete_list:
		del current_planes[plane]



			

