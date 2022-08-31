from bs4 import BeautifulSoup
import requests
import sqlite3
from datetime import datetime
from loggit import loggit

counter=0
start_time=datetime.now()
"""
def add_to_unknown_planes(icao):
    global counter
    if '~' in icao:
        print("~ detected in icao - dont lookup in blackswan" )
        return(None,None)

    try:
        print('Lookup in blackswan')
        counter = counter + 1
        r = requests.get('https://blackswan.ch/aircraft/{}'.format(icao))
        page= r.text
        soup = BeautifulSoup(page,"html.parser")
        reg = soup.find("td" ,attrs={"data-target" :"reg"})
        #model = soup.find("td" ,attrs={"data-target" :"model"}).text
        model = soup.find("td" ,attrs={"data-target" :"type"})
        instant = datetime.now()
        the_diff = instant - start_time
        in_seconds = the_diff.total_seconds()
        in_days = in_seconds/(60*60*24)
        requests_per_day = counter/in_days
        print("{} requests total, which is {} per day after {} days".format(counter,requests_per_day,in_days)) 

        if reg == None or model == None:
            loggit("blackswan has no data for {}".format(icao))
            return(None,None)
        else:
            regt = reg.text
            modelt = model.text
            con = sqlite3.connect("unknown_planes.sqb")
            con.execute("INSERT INTO planes (icao,registration,type,timestamp,count) VALUES ( '{}','{}','{}','{}','{}' )".format(icao,regt,modelt,datetime.now(),1))
            con.commit()
            con.close()
            loggit("added locally to unkown planes from blackswan data {} {} {}".format(icao,regt,modelt))
            return (regt,modelt)
    except Exception as e:
        loggit('could not add plane  {} to unknown planes database : {}'.format(icao,e))
        return (None,None)
"""

def blackswan_lookup(icao):
    global counter
    if '~' in icao:
        loggit("~ detected in icao - dont lookup in blackswan" )
        return(None,None)

    try:
 
        counter = counter + 1
        the_url = f'https://blackswan.ch/aircraft/{icao}'
        loggit(f'Lookup {icao} in blackswan {the_url}')

        r = requests.get(the_url)
        page= r.text
        soup = BeautifulSoup(page,"html.parser")
        reg = soup.find("td" ,attrs={"data-target" :"reg"})
        #model = soup.find("td" ,attrs={"data-target" :"model"}).text
        model = soup.find("td" ,attrs={"data-target" :"type"})
        instant = datetime.now()
        the_diff = instant - start_time
        in_seconds = the_diff.total_seconds()
        in_days = in_seconds/(60*60*24)
        requests_per_day = counter/in_days
        loggit("{} requests total, which is {} per day after {} days".format(counter,requests_per_day,in_days)) 

        if reg == None or model == None:
            loggit("blackswan has no data for {}".format(icao))
            return(None,None)
        else:
            regt = reg.text
            modelt = model.text
            return (regt,modelt)
    except Exception as e:
        loggit(f'could not find plane  {icao} in blackswan , exception : {e}')
        return (None,None)
