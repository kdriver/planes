
import ADSBExKey
import requests

s = requests.Session()
s.headers.update({'Api-Auth':ADSBExKey.ADSB_KEY})

def adsb_lookup(plane):
        URL= "https://adsbexchange.com/api/aircraft/icao/{0}/".format(plane.upper())
        print("lookup {0}\n".format(URL))
        r = s.get(url=URL)
        answer = r.json()
        aircraft = answer['ac']
        data = []
        if aircraft != None:
            p = aircraft[0]
            if p['reg'] == '':
                return None
            else:
                try:
                    f = p['from']
                    t = p['to']
                    data = { 'icao' : plane, 'tail' : p['reg'] , 'from' : p['from'], 'to':p['to']}
                except:
                    data = { 'icao' : plane, 'tail' : p['reg'] }

                return data
        else:
            return None


