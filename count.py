import json
import time

with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
     data = json.load(f)


planes = data["aircraft"]

t = time.time()
x = t/86400  + 25569
d = int(t) % 86400


with open("/home/pi/planes.txt", "a") as myfile:
    myfile.write("%d,%f,%d,%d\n" % (t,x,d,len(planes)))
