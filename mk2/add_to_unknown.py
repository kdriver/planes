from bs4 import BeautifulSoup
import requests
import sqlite3
from datetime import datetime
from loggit import loggit

def add_to_unknown_planes(icoa):
    try:
        print('Lookup in blackswan')
        r = requests.get('https://blackswan.ch/aircraft/{}'.format(icoa))
        page= r.text
        soup = BeautifulSoup(page,"html.parser")
        reg = soup.find("td" ,attrs={"data-target" :"reg"})
        #model = soup.find("td" ,attrs={"data-target" :"model"}).text
        model = soup.find("td" ,attrs={"data-target" :"type"})
        if reg == None or model == None:
            loggit("blackswan has no data for {}".format(icoa))
            return(None,None)
        else:
            regt = reg.text
            modelt = model.text
            con = sqlite3.connect("unknown_planes.sqb")
            con.execute("INSERT INTO planes (icoa,registration,type,timestamp,count) VALUES ( '{}','{}','{}','{}','{}' )".format(icoa,regt,modelt,datetime.now(),1))
            con.commit()
            con.close()
            loggit("added locally to unkown planes from blackswan data {} {} {}".format(icoa,regt,modelt))
            return (regt,modelt)
    except Exception as e:
        loggit('could not add plane  {} to unknown planes database : {}'.format(icoa,e))
        return (None,None)

