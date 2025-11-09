""" This module uses reference data to enrich the plane records """
import subprocess

import sqlite3
import os
import sys
# import csv
import time
from loggit import loggit
# from loggit import TO_FILE,TO_SCREEN
from loggit import BOTH
from loggit import RED_TEXT 
from data_service import DataService

conn=None
conn_base=None
# adsb_cache=None

consolidated_data = None

aircraft_data_map={}

#last_updated = time.time() - (60*60*25)
interval = (60*60*24)
if os.getenv("UPDATE") is not None:
    last_updated = time.time() - ( 2*interval)
else:
    last_updated = time.time() 


create_text = """ CREATE TABLE IF NOT EXISTS cache ( id integer primary key autoincrement,  hex text, tail text,type text , seen integer); """ 
cols = "  hex , tail , type , seen  " 

def ascii_time():
    """ Return an ascii time string """
    return time.asctime( time.localtime(time.time()))



def call_command(command):
    txt = subprocess.check_output(command,stderr=subprocess.STDOUT)
    if isinstance(txt,bytes):
        val = txt.decode('utf-8')
    else:
        val = txt

    loggit(val)

    return val

def init_reference_data():
    global conn
    global conn_base
    global consolidated_data
    loggit("Connecting to databases")
    loggit("Consolidated data")
    consolidated_data = DataService("consolidated_data.sqb")
    loggit("Standing data")
    conn = sqlite3.connect('StandingData.sqb')
    loggit("Base station ")
    conn_base = sqlite3.connect('./BaseStation.sqb')
    
    loggit("Connected to databases")

def update_reference_data():
    global last_updated,conn,conn_base
    tnow = time.time()
    if ( tnow - last_updated ) > interval:
        last_updated = tnow
        try:
            conn.close()
            conn_base.close()
            loggit("call script and try to refresh databasei {}".format(ascii_time()))
            call_command(["./update_BaseStation.sh"])
            loggit("script returned")
            conn_base = sqlite3.connect('./BaseStation.sqb')
            conn = sqlite3.connect('./StandingData.sqb')
        except Exception as my_e:
            print(f"Complete disaster - cant update the databases {my_e} ")
            sys.exit()
        loggit(f"\nupdates completed on {time.time()-tnow:.2f} seconds\n")


def add_route(plane):
    """ Add the route from the flight data """
    #global conn
    if 'flight' not in plane:
        return
    answer = conn.execute("SELECT FromAirportName,ToAirportName  FROM RouteView WHERE Callsign = '%s'" % plane['flight'].strip() )
    txt = answer.fetchone()
    if txt is not None and txt[0] is not None:
        route = "%s -> %s" % ( txt[0], txt[1])
        #loggit("got route from sql %s " % route , TO_FILE)
        plane['route'] = route

def add_tail_and_type(icao,plane):
    """ look up the tail from icao hex """
    answer = consolidated_data.get_country(icao)
    plane['icao_country'] = answer
    
    if consolidated_data.is_suppressed(icao):
        return None
    
    answer = consolidated_data.lookup(icao)
    if answer is None:
        return None
    plane['tail'] = answer[0]
    plane['plane'] = answer[1]
    return answer

def add_reference_data(icao,plane):
    """ look up the tail from icao hex , and route data if known"""
    result = add_tail_and_type(icao,plane)
    if result is None and '~' not in icao:
        loggit("add_reference_data no tail found {}".format(icao),BOTH,RED_TEXT )

    if 'route' not in plane:
        add_route(plane)
    return result

def flush_suppression_list():
    """ Invoke the flushing of the supress list that prevents too many API lookups """
    consolidated_data.flush_suppress_list()

def is_suppressed(icao):
    """ Is the plane in the suppression list """
    return consolidated_data.is_suppressed(icao)

def plane_seen(icao):
    consolidated_data.plane_seen(icao)

if __name__ == "__main__":
    init_reference_data()
    last_updated = time.time() - ( 2*interval)
    update_reference_data()
