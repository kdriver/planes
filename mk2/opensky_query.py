
import requests
from loggit import loggit, init_loggit, TO_DEBUG
import time

s = requests.Session()
# s.headers.update({'Api-Auth':ADSBExKey.ADSB_KEY})

def opensky_lookup(plane):
    URL= "https://opensky-network.org/api/metadata/aircraft/icao/{0}/".format(plane.strip().upper())
    loggit(f"   lookup {URL} in opensky network", TO_DEBUG)
    try:
        r = s.get(url=URL, timeout=10)
    except Exception as e:
        loggit("    Error looking up in opensky  {}".format(e), TO_DEBUG)
        return None

    if r.status_code != 200:
        loggit(f"   Opensky lookup {plane} HTTP error {r.status_code}", TO_DEBUG)
        return None
  
    answer = r.json()
    data = []
    if answer is not None:
        if answer['registration'] == '':
            return None
        else:
            #loggit(json.dumps(answer,indent=4))
            data = { 'icao' : plane, 'tail' : answer['registration'] , 'type' : answer['typecode']}
            loggit(f"   Data Returned {data}", TO_DEBUG)
            return data
    else:
        loggit(f'No JSON in OpenSky response for plane {plane}', TO_DEBUG)
        return None

if __name__ == "__main__":
    init_loggit("/tmp/a","/tmp/b","/tmp/c")
    plane="4b1814"
    answer = opensky_lookup(plane)
    if answer is not None :
        print(answer)
    plane="9b1814"
    time.sleep(1)
    answer = opensky_lookup(plane)
    if answer is not None :
        print(answer)
    else:
        print(f"no plane found for {plane}")
