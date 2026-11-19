
import ADSBExKey
import requests
from loggit import loggit, TO_DEBUG

s = requests.Session()
s.headers.update({'Api-Auth':ADSBExKey.ADSB_KEY})

def adsb_lookup(plane):
    URL= "https://adsbexchange.com/api/aircraft/icao/{0}/".format(plane.strip().upper())
    loggit(f"   lookup {URL} in adsbexchange", TO_DEBUG)
    try:
        r = s.get(url=URL, timeout=10)
    except Exception as e:
        loggit("Error looking up in adsb exchange {}".format(e), TO_DEBUG)
        return None
    answer = r.json()
    aircraft = answer['ac']
    data = []
    if aircraft is not None:
        p = aircraft[0]
        if p['reg'] == '':
            return None
        else:
            #loggit(json.dumps(answer,indent=4))
            try:
                data = { 'icao' : plane, 'tail' : p['reg'] , 'from' : p['from'], 'to':p['to'] , 'type' :p['type']}
            except:
                data = { 'icao' : plane, 'tail' : p['reg'], 'type':p['type'] }

            loggit(f"Data Returned {data}", TO_DEBUG)
            return data
    else:
        return None


