""" This module uses reference data to enrich the plane records """
import subprocess

import sqlite3
import os
import csv
import time
from loggit import loggit
from loggit import TO_FILE,TO_SCREEN
from loggit import BOTH
from loggit import RED_TEXT 
# import adsbex_query
# from add_to_unknown import add_to_unknown_planes
from data_service import DataService as DataService

conn=None
conn_base=None
adsb_cache=None

consolidated_data = None

modes_map={}
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

def attach_adsbex_cache():
    global adsbex_cache
    try:
        adsbex_cache = sqlite3.connect("adsbex_cache.sqb")
        cur = adsbex_cache.cursor()
        cur.execute(create_text)
        adsbex_cache.commit()
        loggit("adsbex cache attached")
    except Exception as e:
        print("adsbex cache exception {}".format(e))

attach_adsbex_cache()


def insert_adsbex_cache(data_tuple):
    global adsbex_cache
    try:
        cur = adsbex_cache.cursor()
        cur.execute("INSERT INTO cache(%s) VALUES (?,?,?,?)" % cols,data_tuple)
        adsbex_cache.commit()
        loggit("cached in adsb_cache")
    except Exception as e:
        print("insert into adsbex exception {}".format(e))


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
    global modes_map
    global consolidated_data
    loggit("Connecting to databases")
    loggit("Consolidated data")
    consolidated_data = DataService("consolidated_data.sqb")
    loggit("Standing data")
    conn = sqlite3.connect('StandingData.sqb')
    loggit("Base station ")
    conn_base = sqlite3.connect('./BaseStation.sqb')
    loggit("ModeS list ")
    modes_file = open("./modes.tsv")
    read_tsv = csv.reader(modes_file,delimiter='	')
    modes_map={}
    counter=0
    # for row in read_tsv:
    #     try:
    #         modes_map[row[2]] = row[4]
    #         counter=counter+1
    #     except:
    #         pass
    #     if not(counter % 1000):
    #         print(".",end='',flush=True)
    """
    loggit("\nbasic AC database")
    counter = 0
    with open('basic-ac-db.json') as f:
        while True:
            global aircraft_data_map
            try:
                counter = counter + 1
                line = f.readline()
                if not line:
                    break
                ac = json.loads(line)
                ac_data = [ ac["reg"],ac["icao"],ac["manufacturer"],ac["model"]]
                aircraft_data_map[ac['icao']] = ac_data
                if not(counter % 1000):
                    print(".",end='',flush=True)
            except Exception as e:
                print("error parsing {} in basic-ac-db.json {}".format(line,e))
        """
            
    
        
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
            ans = call_command(["./update_BaseStation.sh"])
            loggit("script returned")
            conn_base = sqlite3.connect('./BaseStation.sqb')
            conn = sqlite3.connect('./StandingData.sqb')
            # modes_file = open("./modes.tsv")
            # read_tsv = csv.reader(modes_file,delimiter='	')
            # modes_map={}
            # for row in read_tsv:
            #     modes_map[row[2]] = row[4]
        except Exception as e:
            print("Complete disaster - cant update the databases  " % e)
            exit()
        loggit("\nupdates completed on {:.2f} seconds\n".format(time.time()-tnow))


"""  
            txt = "refresh the route database %s\n"  % ascii_time()
            loggit(txt)
            try:
                #conn.close() 
                loggit("call wget command for StandingData")
                ans = call_command(["/usr/bin/wget","-N","http://www.virtualradarserver.co.uk/Files/StandingData.sqb.gz"])
                loggit("wget command returned")
                if  'Omitting' in ans :
                    loggit("No download - so no need to decompress \n")
                else:
                    loggit("decompress StandingData")
                    call_command(["gunzip","-f","-k","./StandingData.sqb.gz"])
                conn = sqlite3.connect('./StandingData.sqb')
                loggit("Reconnected to StandingData - the route database")
                
            except Exception as e:
                print("Complete disaster - cant re open route database {}".format(e))
            txt = "refresh the BaseStation  database %s\n"  % ascii_time()
            loggit(txt)
"""

"""
Superceded by add_tail_and_type_2
def add_tail_and_type(icao,plane):
    # find the tail, plane type and route
    reg = None
    ptype = None
    # global conn_base
    # global adsbex_cache
    the_hex = icao.strip().upper()
    # lookup in Basestation.sqb
    try:
        answer = conn_base.execute("SELECT Registration,Manufacturer,ICAOTypeCode,RegisteredOwners  FROM Aircraft WHERE ModeS = '%s'" % str(the_hex) )
        txt = answer.fetchone()
        if txt is not None:
            if  txt[0] is not None:
                reg = "%s" % txt[0]
                #loggit("{} got tail {} from Basestation".format(the_hex,reg),TO_FILE)
            if txt[1] is not None:
                plane['Manufacturer'] = "{}".format(txt[1])
            if txt[2] is not None:
                ptype = "{}".format(txt[2])
            if txt[3] is not None:
                plane['Owner'] = "{}".format(txt[3])
    except Exception as e:
        print("get_reg - database exception %s " % e )

    # lookup in ModeS tsv
    # if reg == None:
    #     if the_hex in modes_map:
    #         reg = modes_map[the_hex]

    # lookup in local copy of ADSB Exchange cache
    if reg is None:
        answer = adsbex_cache.execute("SELECT tail,type from cache WHERE hex = '{}'".format(the_hex))
        txt = answer.fetchone()
        if txt is not None and txt[0] is not None:
            #loggit("{} got tail and type from adsbex cached data {} {}".format(the_hex,txt[0],txt[1]),TO_FILE)
            reg = txt[0]
            ptype = txt[1]
            answer = adsbex_cache.execute("UPDATE cache SET seen = seen + 1 WHERE hex = '{}'".format(the_hex))
            adsbex_cache.commit()

    # if we've never been able to find data on this hex value beofre we store it in unknown planes so we wont try and look it up again    
    if reg is None:
        try:
            conn_unknown = sqlite3.connect("unknown_planes.sqb")
            answer = conn_unknown.execute("SELECT registration,type from planes WHERE icao = '{}'".format(the_hex))
            txt = answer.fetchone()
            if txt is not None and txt[0] is not None:
                reg = txt[0]
                ptype = txt[1]
                conn_unknown.execute("UPDATE planes SET count = count + 1 WHERE icao = '{}'".format(the_hex))
                conn_unknown.commit()
                loggit("{} got tail and type from local unknown_planes database {} {}".format(the_hex,reg,ptype),TO_FILE)
            conn_unknown.close()
        except Exception as e:
            loggit("problem reading unknown_planes database {}".format(e))

    # if we still haven't found it, try to look it up in adsbex   
    if reg is None:
        try:
            adsb = adsbex_query.adsb_lookup(the_hex)
        except Exception as e:
            loggit("adsb lookup exception {}".format(e),BOTH)
            adsb = None

        if adsb is not None:
            reg = adsb['tail']
            ptype = adsb['type']
            insert_adsbex_cache((the_hex,reg,ptype,1))
            if 'from' in adsb:
                plane['route'] = "{}->{}".format(adsb['from'],adsb['to'])

    # we've tried the sql databases, the ADSB online cache and previously unknown planes ... so add this one to unknown planes
    if reg is None:
        loggit("could not find tail for {}".format(the_hex),BOTH,RED_TEXT)
        reg,ptype = add_to_unknown_planes(icao)

    if reg is not None:
        plane['tail'] = reg
    if ptype is not None:
        plane['plane'] = ptype


    #loggit("enriched result {} {}".format(icao , reg),TO_SCREEN)

    return reg
"""

def add_route(plane):
    """ Add the route from the flight data """
    #global conn
    if 'flight' not in plane:
        return
    answer = conn.execute("SELECT FromAirportName,ToAirportName  FROM RouteView WHERE Callsign = '%s'" % plane['flight'].strip() )
    txt = answer.fetchone()
    if txt is not None and txt[0] != None:
        route = "%s -> %s" % ( txt[0], txt[1])
        #loggit("got route from sql %s " % route , TO_FILE)
        plane['route'] = route

def add_tail_and_type_2(icao,plane):
    """ look up the tail from icao hex """
    answer = consolidated_data.lookup(icao)
    if answer is None:
        return None
    plane['tail'] = answer[0]
    plane['plane'] = answer[1]
    return answer

def add_reference_data(icao,plane):
    """ look up the tail from icao hex , and route data if known"""
    result = add_tail_and_type_2(icao,plane)
    if result is None and '~' not in icao:
        loggit("add_reference_data no tail found {}".format(icao),BOTH,RED_TEXT )

    if 'route' not in plane:
        add_route(icao,plane)
    return result


if __name__ == "__main__":
    last_updated = time.time() - ( 2*interval)
    update_reference_data()
