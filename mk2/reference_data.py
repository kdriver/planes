import subprocess
import time
from loggit import loggit
from loggit import TO_FILE
from loggit import BOTH
from loggit import RED_TEXT as RED_TEXT
import sqlite3
import csv
import adsbex_query

conn=None
conn_base=None
adsb_cache=None

modes_map={}
last_updated = time.time() 
#last_updated = time.time() - (60*60*25)
interval = (60*60*24)


create_text = """ CREATE TABLE IF NOT EXISTS cache ( id integer primary key autoincrement,  hex text, tail text,type text , seen integer); """ 
cols = "  hex , tail , type , seen  " 

def ascii_time():
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
    except Exception as e:
        print("insert into adsbex exception {}".format(e))


def call_command(command):
    t = time.time()
    txt = str(subprocess.check_output(command,stderr=subprocess.STDOUT))
    loggit(txt)
    return txt

def init_reference_data():
        global conn
        global conn_base
        global modes_map
        loggit("Connecting to databases")
        loggit("Standing data")
        conn = sqlite3.connect('StandingData.sqb')
        loggit("Base station ")
        conn_base = sqlite3.connect('./BaseStation.sqb')
        loggit("Modes list ")
        modes_file = open("./modes.tsv")
        read_tsv = csv.reader(modes_file,delimiter='	')
        modes_map={}
        counter=0
        for row in read_tsv:
            modes_map[row[2]] = row[4]
            counter=counter+1
            if not(counter % 1000):
                print(".",end='',flush=True)
                
        loggit("Connected to databases")

def update_reference_data():
        global last_updated
        tnow = time.time()
        if ( tnow - last_updated ) > interval:
            last_updated = tnow  
            txt = "refresh the route database %s\n"  % ascii_time()
            loggit(txt)
            try:
                #conn.close() 
                print("call wget command ")
                ans = call_command(["/usr/bin/wget","-N","http://www.virtualradarserver.co.uk/Files/StandingData.sqb.gz"])
                print("wget command returned")
                if  'Omitting' in ans :
                    print("No download - so no need to decompress \n")
                else:
                    call_command(["gunzip","-f","-k","./StandingData.sqb.gz"])
                conn = sqlite3.connect('./StandingData.sqb')
            except Exception as e:
                print("Complete disaster - cant re open route databasei {}".format(e))
            txt = "refresh the BaseStation  database %s\n"  % ascii_time()
            loggit(txt)
            try:
                #conn_base.close() 
                loggit("call script and try to refresh database")
                ans = call_command(["./update_BaseStation.sh"])
                loggit("script returned")
                conn_base = sqlite3.connect('./BaseStation.sqb')
                loggit("reconnected to the Base station database %s"  % ascii_time())
                modes_file = open("./modes.tsv")
                read_tsv = csv.reader(modes_file,delimiter='	')
                modes_map={}
                for row in read_tsv:
                    modes_map[row[2]] = row[4]
            except Exception as e:
                print("Complete disaster - cant re open Base station database %s " % e)
                exit()
            loggit("updates completed\n")


def add_tail_and_type(icoa,plane):
    # find the tail, plane type and route
    reg = None
    ptype = None
    global conn_base
    global  adsbex_cache
    the_hex = icoa.strip().upper()
    try:
        answer = conn_base.execute("SELECT Registration,Manufacturer,ICAOTypeCode,RegisteredOwners  FROM Aircraft WHERE ModeS = '%s'" % str(the_hex) )
        txt = answer.fetchone()
        if txt != None:
            if  txt[0] != None:
                reg = "%s" % txt[0]
                loggit("{} got tail {} from Basestation".format(the_hex,reg),TO_FILE)
            if txt[1] != None:
                plane['Manufacturer'] = "{}".format(txt[1])
            if txt[2] != None:
                ptype = "{}".format(txt[2])
            if txt[3] != None:
                plane['Owner'] = "{}".format(txt[3])
    except Exception as e:
        print("get_reg - database exception %s " % e )

    if reg == None:
        if the_hex in modes_map:
            reg = modes_map[the_hex]
    
    if reg == None:
        answer = adsbex_cache.execute("SELECT tail,type from cache WHERE hex = '{}'".format(the_hex))
        txt = answer.fetchone()
        if txt != None and txt[0] != None:
            loggit("{} got tail and type from adsbex cached data {} {}".format(the_hex,txt[0],txt[1]),TO_FILE)
            reg = txt[0]
            ptype = txt[1]
            answer = adsbex_cache.execute("UPDATE cache SET seen = seen + 1 WHERE hex = '{}'".format(the_hex))
            adsbex_cache.commit()
    
    if reg == None:
        try:
            adsb = adsbex_query.adsb_lookup(the_hex)
        except Exception as e:
            loggit("adsb lookup exception {}".format(e),BOTH)
            adsb = None

        if adsb != None:
            reg = adsb['tail']
            ptype = adsb['type']
            insert_adsbex_cache((the_hex,reg,ptype,1))
            if 'from' in adsb:
                    plane['route'] = "{}->{}".format(adsb['from'],adsb['to'])
    if reg == None:
        loggit("could not find tail for {}".format(the_hex),BOTH,RED_TEXT)
    if reg != None:
        plane['tail'] = reg
    if ptype != None:
        plane['plane'] = ptype

def add_route(icoa,plane):
    global conn
    if 'flight' not in plane:
        return
    answer = conn.execute("SELECT FromAirportName,ToAirportName  FROM RouteView WHERE Callsign = '%s'" % plane['flight'].strip() )
    txt = answer.fetchone()
    if txt  != None and txt[0] != None:
        route = "%s -> %s" % ( txt[0], txt[1])
        loggit("got route from sql %s " % route , TO_FILE)
        plane['route'] = route

def add_reference_data(icoa,plane):
    add_tail_and_type(icoa,plane)
    if 'route' not in plane:
        add_route(icoa,plane)
