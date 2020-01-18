import json
import time
import pprint
import math
import requests
import os
import sqlite3
import sqldb
import Adafruit_DHT
import adsbex_query

from influxdb import InfluxDBClient

from birdy.twitter import UserClient
import twittertokens
import thingspeak

use_aeroplanes_api=False

client = UserClient(twittertokens.CONSUMER_KEY,twittertokens.CONSUMER_SECRET,
                    twittertokens.ACCESS_TOKEN,twittertokens.ACCESS_TOKEN_SECRET)

influx= InfluxDBClient("192.168.0.106",8086,'','',"planes")
influx_local = InfluxDBClient("localhost",8086,'','',"planes")
thingspeak_key=thingspeak.WRITE_KEY

me=[-1.95917,50.83583]

record_period=6
interval=60*60*24.0
#force database update on restart
last_updated=time.time()  - (2*interval)

log = open("monitor.txt","a")

import subprocess

def check_delay(t,delta,msg):
        n = time.time()
        if ( (n - t) > delta ):
            txt = msg + " actual time is %d \n" % (n-t) 
            print(txt)
            log.write(txt)

def ascii_time(t):
    return time.asctime( time.localtime(time.time()))

def call_command(command):
    t = time.time()
    txt = subprocess.check_output(command,stderr=subprocess.STDOUT)
    print(txt)
    log.write(txt)
    check_delay(t,2," call_command took too long ")
    return txt


def update_routes(tnow):
        global last_updated
        if ( tnow - last_updated ) > interval:
            last_updated = tnow  
            global conn
            global conn_base
            txt = "refresh the route database %s\n"  % ascii_time(time.time())
            print(txt)
            log.write(txt)
            try:
                #conn.close() 
                ans = call_command(["wget","-N","http://www.virtualradarserver.co.uk/Files/StandingData.sqb.gz"])
                if  'Omitting' in ans :
                    print("No download - so no need to decompress \n")
                else:
                    call_command(["gunzip","-f","-k","./StandingData.sqb.gz"])
                conn = sqlite3.connect('StandingData.sqb')
                print("reconnected to the route database %s"  % ascii_time(time.time() ))
                log.write("reconnected to the route database %s\n"  % ascii_time(time.time() ))
                log.flush()
            except:
                print("Complete disaster - cant re open route database")
            txt = "refresh the BaseStation  database %s\n"  % ascii_time(time.time())
            print(txt)
            log.write(txt)
            try:
                #conn_base.close() 
                print("call script 'try' to refresh database")
                ans = call_command(["./update_BaseStation.sh"])
                print("script returned")
                print(ans)
                #ans = call_command(["wget","-N","https://data.flightairmap.com/data/basestation/BaseStation.sqb.zip"])
                #if 'Omitting' in ans : 
                #    print("No download - so no need to decompress \n")
                #else:
                #    call_command(["unzip","-o","./BaseStation.sqb.zip"])
                conn_base = sqlite3.connect('./basestation/BaseStation.sqb')
                print("reconnected to the Base station database %s"  % ascii_time(time.time() ))
                log.write("reconnected to the Base station database   %s\n"  % ascii_time(time.time() ))
                log.flush()
            except Exception as e:
                print("Complete disaster - cant re open Base station database %s " % e)
                exit()
update_routes(time.time())



cpu_temp="40"
humidity, last_temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, 4)
print(humidity,last_temperature)

def thingspeak(num,persec):
    request= "https://api.thingspeak.com/update?api_key=%s&field1=%s&field2=%s&field3=%s" % (thingspeak_key,num,persec,cpu_temp)
    t = time.time()
    try:
        response = requests.post(request)
    except:
        print("error writing to thingspeak \n")
    check_delay(t,4," thingspeak  write took too long ")



def write_to_database(json_body):
            if ( 0 ) :
                t = time.time()
                try:
                    influx.write_points(json_body)
                except:
                    print("failed to write to mac db %s\n" % ascii_time(t))

                check_delay(t,2," influx db  106 write took too long ")

            t = time.time()
            try:
                influx_local.write_points(json_body)
            except Exception as e:
                print("failed to write to rpi db %s %s\n" % (ascii_time(t),e))
            check_delay(t,2," influx db localhost write took too long ")


def measure_temp():
    #read the internal rpi temp sensor
            temp = os.popen("vcgencmd measure_temp").readline()
            t = temp.replace("temp=","")
            t = float(t.replace("'C",""))
            global cpu_temp
            cpu_temp = str(t)
    #read the external dht22 one wire temp/sumidity sensor
            humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, 4)
            if humidity == None:
                    humidity = 50.0
            if humidity > 100:
                    humidity = 100
            if temperature == None or temperature > 50:
                temperature = 100.0
            # The dh22 sensor seems to return readings that are a bit low everynow and again so ignore them and use the last 'good' value
            global last_temperature
            if abs(last_temperature-temperature) > 1.0:
                txt = "{2} fixed temp sensor, new reading {0}, last reading {1}\n".format( temperature, last_temperature,ascii_time(time.time()))
                print(txt)
                log.write(txt)
                temperature = last_temperature
            else:
                last_temperature = temperature

            json_body = [
                        {
                                    "measurement": "count",
                                            "fields": {
                                                            "rpi_temp":  t,
                                                            "dht22_temp_a": temperature,
                                                            "dht22_humidity": humidity
                                                  }
                                                }]
            write_to_database(json_body)
            return (t,temperature,humidity)

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
        print("connected to StandingData")
except Exception as e: 
	print (e)
	exit()

try:
        conn_base = sqlite3.connect('basestation/BaseStation.sqb')
        print("connected to BaseStation")
except Exception as e: 
	print (e)
	exit()

import signal

def handler(signum,stack):
        dmp = open("dump.txt","w")
        tnow = time.time()
        dmp.write(" time  %s " % time.asctime( time.localtime( tnow  )))
        for plane_hex in current_planes:
            plane=current_planes[plane_hex]
            dmp.write("%s\n" % plane)
        dmp.write("last time the temp was recorded is %s " % time.asctime( last_recorded_temp_time ))
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
log.write("New session %s \n" % (the_time))
log.flush()

adsb_data = open('adsb_data.json',"a")

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


def is_in_db(flight):
            try:
                ms = flight.strip().upper()
                command=  "SELECT Registration  FROM Aircraft WHERE ModeS='{0}'".format(ms)
                answer = conn_base.execute(command)
                txt = answer.fetchone()
                if txt != None:   # If there is an entry
                    if txt[0] != None:  # if there a tail registration field
                        return True
                    else:
                        return False
                else:
                    return False
            except Exception as e:
                print("Exception probing db for hex {0} : {1}".format(flight,e))


def get_reg(flight):
#	return ' '
        t = time.time()
        try:
	    answer = conn_base.execute("SELECT Registration  FROM Aircraft WHERE ModeS = '%s'" % str(flight.strip().upper()) )
            txt = answer.fetchone()
            if txt != None:
                return "%s" % txt
            else:
                return "unknown"
        except Exception as e:
            print("get_reg - database exception %s " % e )

            

        answer="not used"
        if  use_aeroplanes_api :
            url=reg_url+flight
            url=url.strip()
            dprint("D: get reg %s " % url )
            response=requests.post(url)
            dprint("D: got  reg %s " % response.text )
            answer= response.text

        check_delay(t,2," get_reg took too long ")
        print("get_reg not in Basestation data %s API returned %s " % ( flight,answer ))

	return response.text
	
def get_plane(hex_id):
        print("get the plane type for {}".format(hex_id))
        try:
            ms = hex_id.strip().upper()
            command=  "SELECT Manufacturer,Type  FROM Aircraft WHERE ModeS='{0}'".format(ms)
            #print("the_command {0} \n".format(command) )
            answer = conn_base.execute(command )
            txt = answer.fetchone()
            if txt != None:
                x =  "{0}:{1}".format(txt[0],txt[1])
                y = x.split('/')
                answer  = y[0] 
                return answer 
        except Exception as e:
            print("get_plane - flight {0} database exception {1} ".format(hex_id,e) )
            return "unknown" 

def old_get_plane(hex_id):
        try:
            answer = conn_base.execute("SELECT Type  FROM Aircraft WHERE ModeS = '%s'" % str(hex_id.strip().upper()) )
            txt = answer.fetchone()
            if txt != None:
                x =  "%s" % txt
                y = x.split('/')
                answer  = y[0] 
                return answer 
        except Exception as e:
            print("get_plane - flight %s database exception %s " % (hex_id,e) )


        answer="not used"
        if  use_aeroplanes_api :
            url=plane_url+flight
            url=url.strip()
            dprint("D: get plane %s " % url )
            response=requests.post(url)
            dprint("D: got plane %s " % response.text )
            answer=response.text

        check_delay(t,2," get_plane took too long ")
        print("get_plane not in Basestation data %s API returned %s " % ( flight,response.text ))

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
                thingspeak(str(num),str(per_sec)) 

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
                                if miles < 50: 
                                        indb= False
                                        try:
                                            indb= this_plane["indb"]
                                        except:
                                            if is_in_db(this_plane["hex"]) :
                                                indb=True
                                                this_plane["indb"] = True
                                            else:
                                                this_plane["indb"] = False
                                                msg = "flight {0} not in Basestation.sqb database, suppress further lookups\n".format(this_plane["hex"])
                                                print(msg)
                                                log.write(msg)
                                                adsb = adsbex_query.adsb_lookup(this_plane["hex"])
                                                if adsb != None:
                                                    msg = "but found reg in ADSB Ex API for {0} {1}\n".format(this_plane["hex"],adsb['tail'])
                                                    print(msg)
                                                    log.write(msg)
                                                    adsb_data.write(json.dumps(adsb))
                                                    adsb_data.write("\n")
                                                    adsb_data.flush()
                                                    this_plane["reg"] = adsb['tail']
                                                    this_plane["indb"] = True
                                                    indb = True
                                                    try:
                                                        f = adsb['from']
                                                        this_plane["route"] = "{0}->{1}".format(adsb['from'],adsb['to'])
                                                    except:
                                                        pass
                                                else:
                                                    print("flight {0} not found in ADSBEx api either".format(this_plane["hex"]))

                                        if  indb:
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
#                                                        Sat Feb 16 14:08:39 2019 BEE4350  4057f2 G-FBEJ Embraer ERJ 190-200 Lr   track=254.2  alt=17000 nearest_point=0.814259
                                                        pd = "%s flt=%s  hex=%s  tail=%s  type='%s'  route='%s' track=%s  alt=%s nearest_point=%f " % (time.asctime( time.localtime(time.time()) ),this_plane["flight"],this_plane["hex"],this_plane["reg"], this_plane["plane"],this_plane["route"],this_plane["track"],this_plane["altitude"],this_plane["miles"])
#cols = " ts, flight, hex , tail , alt ,  track , nearest_point , lat  , long   " 
                                                        try:
                                                            sqldb.insert_data((time.time(),this_plane["flight"],this_plane["hex"],this_plane["reg"],this_plane["altitude"],this_plane["track"],this_plane["miles"],this_plane["lat"],this_plane["lon"]))
                                                        except Exception as e :
                                                            print("problem inserting into sqldb %s " % e)

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
                        except Exception as e:
                                pass

			this_plane["touched"] = time.time()
			current_planes[hex] = this_plane
				
                except  :
                    pass

#force temp measurement on startup
last_recorded_temp_time = time.time() - 120

def record_temp(tnow):
    global last_recorded_temp_time
    if ( (tnow - last_recorded_temp_time) > 60 ) :
        t,t1,h = measure_temp()
        print("record temp %f dht22 temp %f dht22 humidity %f %s " % (t,t1,h,the_time))
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

sqldb.attach_sqldb()
update_routes(time.time())

while 1:
	global api_requests
	global record_period
	time.sleep(5)
	read_planes()
	now = time.time()
        update_routes(now)
        tick_tock(now)
	record_temp(now)

	four=0
	delete_list = []
	for plane_hex in current_planes:
		try:
			plane = current_planes[plane_hex]
			last_time = plane["touched"]
			td = now - last_time

			if  td  > 60.0:
				delete_list.append( plane_hex )
		except :
			pass

	for plane in delete_list:
		del current_planes[plane]



			

