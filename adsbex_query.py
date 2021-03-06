
import ADSBExKey
import requests
import json

s = requests.Session()
s.headers.update({'Api-Auth':ADSBExKey.ADSB_KEY})

def adsb_lookup(plane):
        URL= "https://adsbexchange.com/api/aircraft/icao/{0}/".format(plane.upper())
        print("lookup {0} online".format(URL))
        r = s.get(url=URL)
        answer = r.json()
        aircraft = answer['ac']
        data = []
        if aircraft != None:
            p = aircraft[0]
            if p['reg'] == '':
                return None
            else:
                print(json.dumps(answer,indent=4))
                try:
                    data = { 'icao' : plane, 'tail' : p['reg'] , 'from' : p['from'], 'to':p['to'] , 'type' :p['type']}
                except:
                    data = { 'icao' : plane, 'tail' : p['reg'], 'type':p['type'] }

                return data
        else:
            return None


