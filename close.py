import json
import time
import pprint
import math
import requests
import os
import sqlite3

from influxdb import InfluxDBClient

from birdy.twitter import UserClient
import twittertokens

client = UserClient(twittertokens.CONSUMER_KEY,twittertokens.CONSUMER_SECRET,
                    twittertokens.ACCESS_TOKEN,twittertokens.ACCESS_TOKEN_SECRET)

influx= InfluxDBClient("192.168.0.106",8086,'','',"planes")
influx_local = InfluxDBClient("localhost",8086,'','',"planes")

me=[-1.95917,50.83583]


def check_delay(t,delta,msg):
        n = time.time()
        if ( (n - t) > delta ):
            txt = msg + " actual time is %d \n" % (n-t) 
            print(txt)
            log.write(txt)

def write_to_database(json_body):
            t = time.time()
            try:
                influx.write_points(json_body)
            except:
                print("failed to write to mac db %s\n" % the_time)

            check_delay(t,2," influx db  106 write took too long ")

            t = time.time()
            try:
                influx_local.write_points(json_body)
            except:
                print("failed to write to rpi db %s \n" % the_time)
            check_delay(t,2," influx db localhost write took too long ")


def measure_temp():
            temp = os.popen("vcgencmd measure_temp").readline()
            t = temp.replace("temp=","")
            t = float(t.replace("'C",""))
            json_body = [
                        {
                                    "measurement": "count",
                                            "fields": {
                                                            "rpi_temp":  t
                                                  }
                                                }]
            write_to_database(json_body)
            return t

def tweet(client,text):
        t = time.time()
	response=''
	try:
		response = client.api.statuses.update.post(status=text)
	except Exception as e:
		print(e)
                print("failed to tweet : retry\n")
                try:
		    response = client.api.statuses.update.post(status=text)
                    print("tweet retry ok\n")
                except Exception as e:
                    print(e)
                    print("failed to tweet a second time\n")

        check_delay(t,2," tweeting  took too long ")
	return response
	
try:
        conn = sqlite3.connect('StandingData.sqb')
        print("connected")
except Exception as e: 
	print (e)
	exit()

import signal

def handler(signum,stack):
        dmp = open("dump.txt","w")
        for plane_hex in current_planes:
            plane=current_planes[plane_hex]
            dmp.write("%s\n" % plane)
        dmp.close()
        print("caught it")

signal.signal(signal.SIGUSR1,handler)

#orgurl='https://ae.roplan.es/api/callsign-origin_IATA.php?callsign='
orgurl="https://ae.roplan.es/api/callsign-origin_IATA.php?callsign="
desturl='https://ae.roplan.es/api/callsign-des_IATA.php?callsign='
plane_url='https://ae.roplan.es/api/hex-type.php?hex='
reg_url='https://ae.roplan.es/api/hex-reg.php?hex='

api_requests=0

the_time = time.asctime( time.localtime(time.time()))
log = open("monitor.txt","a")
log.write("New session %s \n" % (the_time))
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

def dprint(txt):
        if 0 :
            print(txt)

def get_reg(flight):
#	return ' '
        t = time.time()
	url=reg_url+flight
	url=url.strip()
	dprint("D: get reg %s " % url )
	response=requests.post(url)
	dprint("D: got  reg %s " % response.text )
        check_delay(t,2," get_reg took too long ")
	return response.text
	
def get_plane(flight):
#	return ' '
        t = time.time()
	url=plane_url+flight
	url=url.strip()
	dprint("D: get plane %s " % url )
	response=requests.post(url)
	dprint("D: got plane %s " % response.text )
        check_delay(t,2," get_plane took too long ")
	return response.text
	
def get_route(flight):
	global conn
        t = time.time()
	dprint("D: get route %s " % flight )
	answer = conn.execute("SELECT FromAirportName,ToAirportName  FROM RouteView WHERE Callsign = '%s'" % flight.strip() )
	txt = answer.fetchone()
	if txt  != None:
		route = "%s -> %s" % txt
		dprint("D: got route from sql %s " % route )
		return route

	return ' '

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

	dprint("D: got route %s " % route )
        check_delay(t,2," get_route took too long ")
	return route


current_planes =  dict()


def record_planes(num,per_sec):
	json_body = [ { "measurement" : "count",  "tags" : {}, "fields" : { "value" : num , "msgspersec" : per_sec} } ]
	global record_period
	record_period= record_period - 1 
	if ( record_period <= 0 ):
		record_period = 6
                write_to_database(json_body)

def record_overhead(distance):
                json_body = [ { "measurement" : "count",  "tags" : {}, "fields" : { "overhead" : 1 , "distance" : distance} } ]
                write_to_database(json_body)
                return
old_time=0
old_messages=0

def read_planes() :
	with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
		try:
			data = json.load(f)
		except:
                        print("error - cant open arcraft.json")
			return

        the_time = time.asctime( time.localtime(time.time()))
	time_now = data["now"]
	messages_now = data["messages"]
	planes = data["aircraft"]

	this_plane = {}

	global api_requests
	global log
	global old_time
	global old_messages
	api_requests = 0 

	num_planes = len(planes ) 
	time_diff = time_now - old_time
	messages_diff = messages_now - old_messages
	msgs_per_sec = messages_diff / time_diff

	print(" planes in list %d msgs per sec %f" % (num_planes,msgs_per_sec ))

	old_time = time_now
	old_messages = messages_now
	
	record_planes(num_planes,msgs_per_sec)
	touched =0
	iter=0
	for plane in planes:
		iter = iter +1
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

#					print("D: plane %d %s  distance %f old %f " % (iter,this_plane["plane"],miles,this_plane["miles"]))

                                        if miles <= this_plane["miles"]:
                                                this_plane["miles"] = miles
                                                try:
                                                        del this_plane["done"]
                                                except:
                                                        pass
                                        else:
                                                token=""
                                                try:
                                                        pdone = this_plane["done"]
                                                except:
                                                        this_plane["done"]=1
                                                        pd = "%s %s %s %s %s %s track %s  alt=%s nearest point %8.2f " % (time.asctime( time.localtime(time.time()) ),this_plane["flight"],this_plane["hex"],this_plane["reg"], this_plane["plane"],this_plane["route"],this_plane["track"],this_plane["altitude"],this_plane["miles"])
                                                        if this_plane["miles"] < 2.0:
                                                                token="\033[1;32;40m"
                                                                log.write("TWEET   : ")
                                                                record_overhead(this_plane["miles"])
                                                                try:
									tweet(client,pd)
                                                                except Exception as e: print(e)

                                                        print("%s%s\033[0m" % (token,pd))

                                                        log.write("%s \n" % (pd) )
                                                        log.flush()
                        except:
                                pass

			this_plane["touched"] = time.time()
			touched+=1
			current_planes[hex] = this_plane
				
                except  :
                    pass

#tweet(client,"up and running %s\n" %(the_time))

record_period=6
interval=60*60*24.0
#force database update on restart
last_updated=time.time()  - (2*interval)

import subprocess

def call_command(command):
    t = time.time()
    txt = subprocess.check_output(command,stderr=subprocess.STDOUT)
    print(txt)
    log.write(txt)
    check_delay(t,2," call_command took too long ")

def update_routes():
        tnow = time.time()
        global last_updated
        if ( tnow - last_updated ) > interval:
            last_updated = tnow  
            global conn
            txt = "refresh the route database %s\n"  % time.asctime( time.localtime(time.time()))
            print(txt)
            log.write(txt)
            try:
                conn.close() 
                call_command(["wget","-N","http://www.virtualradarserver.co.uk/Files/StandingData.sqb.gz"])
                call_command(["gunzip","-f","-k","./StandingData.sqb.gz"])
                conn = sqlite3.connect('StandingData.sqb')
                print("reconnected to the route database %s"  % the_time )
                log.write("reconnected to the route database %s\n"  % the_time )
                log.flush()
            except:
                print("Complete disaster - cant re open route database")
                
#force temp measurement on startup
last_recorded_temp_time = time.time() - 120

def record_temp():
    tnow = time.time()
    global last_recorded_temp_time
    if ( (tnow - last_recorded_temp_time) > 60 ) :
        print("record temp %f %s " % (measure_temp(),the_time))
        last_recorded_temp_time = tnow

heartbeat = 0

def tick_tock(c):
    global heartbeat
    diff = c - heartbeat
    if ( diff > 300 ) :
        if ( diff > 350 ):
            d  = " Time PAUSED %d " % (diff)
        else:
            d = ""

        txt = "Tick: %s %s\n" % (d,time.asctime( time.localtime(time.time())))
        print(txt)
        log.write(txt)
        heartbeat = c




while 1:
	global api_requests
	global record_period
        update_routes()
	read_planes()
	record_temp()
	time.sleep(5)
	now = time.time()
	touched=0
        tick_tock(now)

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



			
