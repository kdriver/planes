
import ADSBExKey
import requests
from loggit import loggit

s = requests.Session()
s.headers.update({'Api-Auth':ADSBExKey.ADSB_KEY})

def adsb_lookup(plane):
        URL= "https://adsbexchange.com/api/aircraft/icao/{0}/".format(plane.strip().upper())
        loggit("lookup {0} in adsbexchange".format(URL))
        try:
            r = s.get(url=URL)
        except Exception as e:
            loggit("Error looking up in adsb exchange {}".format(e))
            return None
        answer = r.json()
        aircraft = answer['ac']
        data = []
        if aircraft != None:
            p = aircraft[0]
            if p['reg'] == '':
                return None
            else:
                #loggit(json.dumps(answer,indent=4))
                loggit("Found")
                try:
                    data = { 'icao' : plane, 'tail' : p['reg'] , 'from' : p['from'], 'to':p['to'] , 'type' :p['type']}
                except:
                    data = { 'icao' : plane, 'tail' : p['reg'], 'type':p['type'] }

                return data
        else:
            return None


