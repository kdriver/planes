import json
import time
import pprint
import math

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

def read_planes() :
	with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
	     data = json.load(f)


	planes = data["aircraft"]

	t = time.time()
	x = t/86400  + 25569
	d = int(t) % 86400

	pp = pprint.PrettyPrinter()

#pp.pprint(planes)

	for plane in planes:
		try:
			lat = plane["lat"]
			lon = plane["lon"]
			id = "id: "
			try:
				id = id + " " + plane["flight"]
			except:
				id = id + " noflight "

			try:
				id = id + " " + str(plane["altitude"])
			except:
				id = id + " noaltitude "

			try:
				id = id + " " + plane["hex"]
			except:
				id = id + " nohex "

			miles = Haversine([lon,lat],me).nm
			if miles < 20: 
				print(id,miles)
		except:
			pass

#with open("/home/pi/planes.txt", "a") as myfile:
#    myfile.write("%d,%f,%d,%d\n" % (t,x,d,len(planes)))


while true:
	read_planes()
	sleep(180)
	print("--------")

