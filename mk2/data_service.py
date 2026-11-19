"""   A module to provide enrichment services from reference data downloaded externally to this module """

import os
import sqlite3
import csv
import subprocess
import json
import sys
import requests
import time

from icao_countries import ICAOCountries
import adsbex_query
from opensky_query import opensky_lookup
from bs4 import BeautifulSoup
from datetime import datetime

from loggit import loggit,init_loggit
from loggit import TO_FILE, TO_SCREEN, BOTH, TO_DEBUG

# Tuple index
TAIL = 0
TYPE = 1

class DataService:
    """
    This class manages access to reference data so that 
    we can use the icao hex value to  tail, plane etc
    """
    create_text = """ CREATE TABLE IF NOT EXISTS aircraft ( id integer primary key autoincrement,  
                      hex text, tail text,type text , seen integer, looked_up integer); """
    cols = "  hex , tail , type , seen  , looked_up"
    counter=0
    start_time=datetime.now()

    def __init__(self, data_file):
        try:
            self.create_text = """ CREATE TABLE IF NOT EXISTS aircraft ( id integer primary key autoincrement, 
                                   hex text, tail text,type text , seen integer, looked_up integer); """
            self.cols = "  hex , tail , type , seen  , looked_up"
            self.handle = sqlite3.connect(data_file)
            cursor = self.handle.cursor()
            cursor.execute(self.create_text)
            cursor.execute(self.create_unknown_text)
            self.handle.commit()
            self.black_counter = 0
            self.counter= 0
            self.icao_map = ICAOCountries()
            self.suppress_dict = {}
            self.load_recent_unknowns()
            self.start_time=datetime.now()
            # self.refresh_external_data()
            # self.update_local_cache()
        except Exception as my_e:
            print(my_e)
            print(f"Could not open database {data_file}")
            sys.exit(1)

    # ICAO hex codes that no lookup source could resolve to a tail number.
    # Timestamps are local time, 'YYYY-MM-DD HH:MM:SS'.
    create_unknown_text = """ CREATE TABLE IF NOT EXISTS unknown ( hex text primary key,
                              first_seen text, last_seen text, attempts integer); """

    def load_recent_unknowns(self):
        """ Re-suppress planes that failed lookup in the last 24 hours, so a restart doesn't re-query them """
        rows = self.handle.execute(
            "SELECT hex, strftime('%s', last_seen, 'utc') FROM unknown "
            "WHERE last_seen > datetime('now', 'localtime', '-1 day')").fetchall()
        for the_hex, epoch in rows:
            self.suppress_dict[the_hex] = float(epoch)
        loggit(f"{len(rows)} unknown planes suppressed from the last 24 hours")

    def record_unknown(self, icao):
        """ Record that no source could find a tail for this icao hex """
        try:
            self.handle.execute(
                """INSERT INTO unknown (hex, first_seen, last_seen, attempts)
                   VALUES (?, datetime('now','localtime'), datetime('now','localtime'), 1)
                   ON CONFLICT(hex) DO UPDATE SET last_seen = excluded.last_seen,
                                                  attempts = attempts + 1""",
                (icao.lower(),))
            self.handle.commit()
        except Exception as e:
            loggit(f"record_unknown: error {e} {icao}")

    def reference_index_lookup(self, the_hex):
        """ Look up a hex in reference_index.sqb (built from the downloaded bulk databases
            by build_reference_index.py). Opened per call so a rebuilt index is picked up. """
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reference_index.sqb')
        if not os.path.exists(path):
            return None
        try:
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                return con.execute("SELECT tail, type FROM ref WHERE hex = ?", (the_hex,)).fetchone()
            finally:
                con.close()
        except Exception as e:
            loggit(f"reference index lookup error {e} {the_hex}")
            return None

    def update_the_cache(self):
        self.update_local_cache()

    def plane_seen(self, icao):
        if '~' in icao:
            return
        try:
            the_hex = icao.lower()
            sql_cmd = "UPDATE aircraft SET seen = seen + 1 WHERE hex = ?"
            cursor = self.handle.cursor()
            cursor.execute(sql_cmd, (the_hex,))
            self.handle.commit()
        except Exception as e:
            loggit(f"plane_seen: error {e} {sql_cmd}")

    def call_command(self, command):
        txt = subprocess.check_output(command, stderr=subprocess.STDOUT)
        if isinstance(txt, bytes):
            val = txt.decode('utf-8')
        else:
            val = txt

        loggit(val)

        return val

    def hexdbio_lookup(self,icao):
        if '~' in icao:
            loggit("~ detected in icao - dont lookup in hexdb.io" )
            return(None,None)

        try:
            the_url = f'https://hexdb.io/api/v1/aircraft/{icao}'
            loggit(f' {icao} in hexdb.io {the_url}', TO_DEBUG)

            response = requests.get(the_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tail = data.get('Registration')
                model = data.get('ICAOTypeCode') or data.get('Type')
                if tail and model:
                    return (tail, model)

            if response.status_code == 404:
                loggit(f"hexdb.io has no data for {icao}", TO_DEBUG)

        except Exception as my_e:
            loggit(f"could not find plane in hexdb.io {icao}: {my_e}", TO_DEBUG)

        return (None,None)






    def blackswan_lookup(self,icao):
        if '~' in icao:
            loggit("~ detected in icao - dont lookup in blackswan" )
            return(None,None)

        try:
    
            self.black_counter = self.black_counter + 1
            time_b = time.time()
            the_url = f'https://blackswan.ch/aircraft/{icao}'
            loggit(f' {icao} in blackswan {the_url}', TO_DEBUG)

            r = requests.get(the_url, timeout=10)
            time_diff = time.time() - time_b
            page= r.text
            soup = BeautifulSoup(page,"html.parser")
            reg = soup.find("td" ,attrs={"data-target" :"reg"})
            #model = soup.find("td" ,attrs={"data-target" :"model"}).text
            model = soup.find("td" ,attrs={"data-target" :"type"})
            the_diff = datetime.now() - self.start_time
            in_seconds = the_diff.total_seconds()
            in_days = in_seconds/(60*60*24)
            requests_per_day = self.black_counter/in_days
            loggit(f"bs lookup took {time_diff} secs. {self.black_counter} requests total, which is {requests_per_day} per day after {in_days} days", TO_DEBUG) 

            if reg is None or model is None:
                loggit(f"blackswan has no data for {icao}", TO_DEBUG)
                return(None,None)
            
            regt = reg.text
            modelt = model.text
            return (regt,modelt)
        except Exception as my_e:
            loggit(f'could not find plane  {icao} in blackswan , exception : {my_e}', TO_DEBUG)
            return (None,None)

    def get_country(self, icao):
        return self.icao_map.icao_to_country(icao)
    
    def flush_suppress_list(self):
        """  Flush the list that caches the icoa to prevent too many API lookups """
        now = time.time()
        #if len(self.suppress_dict) > 0:
        #    loggit(f"suppress list :")
        delete_list = []
        for plane in self.suppress_dict.items():
            k,value = plane
            age = now - value
            #loggit(f"   suppress list  {k}, seconds old {age}, hours old {age/3600} hours")
            if age > float(60*60*24):
                delete_list.append(k)
        
        for item in delete_list:
            loggit(f"flush suppress list for {item}",BOTH)
            del self.suppress_dict[item]
            
    
    def is_suppressed(self,icao):
        return icao.lower() in self.suppress_dict

    def insert_row(self,the_hex,the_tail,the_type):
        data = {
                        'tail' : the_tail,
                        'model' : the_type,
                        'icao_hex' : the_hex,
                        'man' : None
                        }
        self.insert(data,True)
        # it has a tail now, so it is no longer unknown
        self.handle.execute("DELETE FROM unknown WHERE hex = ?", (the_hex.lower(),))
        self.handle.commit()

    
    def lookup(self, icao, remote_lookup=True):
        # loggit(" {}".format(icao),BOTH)
        """
        Look for data against the icao hex value and return a list of values found, or None
        """
        try:

            the_hex = icao.lower()

            if '~' in the_hex:  # Its a TIS-B record
                return None
            
            if self.is_suppressed(the_hex):
                #loggit(f"plane {icao} is in the suppress list")
                return None
            rows = self.handle.execute(
                "SELECT tail,type FROM aircraft WHERE hex = ?", (the_hex,))
            row = rows.fetchone()
            if row is not None:
                # loggit("{} found {} in consolidated data".format(the_hex,row),BOTH)
                return row

            if remote_lookup is False:
                return None

            # Try each source in turn. Per-source detail goes to the debug log;
            # the main log gets one summary line per lookup.
            tried = []
            for name, source in self.lookup_sources():
                try:
                    row = source(the_hex)
                except Exception as e_name:
                    loggit(f"{the_hex} {name} lookup exception {e_name}", TO_DEBUG)
                    row = None
                if row and row[0]:
                    row = (row[0], row[1] or '')
                    loggit(f"{the_hex}  {row[0]:<8} {row[1]:<5} from {name}", BOTH)
                    self.insert_row(the_hex, row[0], row[1])
                    return row
                tried.append(name)

            loggit(f"{the_hex}  not found in {', '.join(tried)} - suppressed for 24h", BOTH)
            self.suppress_dict[the_hex] = time.time()
            self.record_unknown(the_hex)

        except Exception as e_name:
            loggit(f"error looking up {icao} {e_name}", TO_FILE)
        return None

    def lookup_sources(self):
        """ (name, fn) pairs tried in order; each fn takes a lowercase hex and returns (tail, type) or None """
        def adsbx(the_hex):
            adsb = adsbex_query.adsb_lookup(the_hex)
            if adsb is not None and adsb['tail'] != 'CONTACTADSBX':
                return (adsb['tail'], adsb['type'])
            return None

        # OpenSky is not here: its metadata API returns 410 Gone, even with
        # credentials. Its data reaches us via the downloaded snapshot in the local index.
        return [('local index', self.reference_index_lookup),
                ('adsbx', adsbx),
                ('hexdb', self.hexdbio_lookup),
                ('blackswan', self.blackswan_lookup)]

    def insert(self, plane_dict, commit_it=False):
        """ Insert a new entry into the database = optional commit for performance"""
        try:
            cursor = self.handle.cursor()
            data_tuple = (plane_dict["icao_hex"].lower(),
                          plane_dict["tail"], plane_dict["model"], 0, 0)
            cursor.execute(
                "INSERT INTO aircraft(%s) VALUES (?,?,?,?,?)" % self.cols, data_tuple)
            loggit("insert {} ".format(data_tuple), TO_DEBUG)
            if commit_it is True:
                self.handle.commit()
        except Exception as e:
            print("insert into local cache exception {}".format(e))

    def update(self, plane):
        """ update the plane column """

        data = (plane["tail"], plane["model"], plane["icao_hex"].lower())
        try:
            # print(data)
            self.handle.execute(
                "UPDATE aircraft SET tail = ?,type = ? WHERE hex = ? ", data)
        except Exception as e:
            print("update local cache exception {}".format(e))
            print("update data  {} {}".format(data,type(data[1])))
            sys.exit()

    def refresh_external_data(self):
        print("Refreshing data from external source")
        self.call_command(["./update_BaseStation.sh"])
        loggit("script returned")

    def update_from_modeS_tsv(self):
        loggit("update from ADSB ModeS tsv")
        with open("./modes.tsv") as modes_file:
            read_tsv = csv.reader(modes_file,delimiter='	')
        counter=0
        inserts=0
        updates=0
        errors=0
        for row in read_tsv:
            try:
                icao = row[2].lower()
                if icao == 'modeS':
                    continue
                local_data = self.lookup(icao,False)
                if local_data is None:
                    # missing data - so insert it
                    loggit("insert modeS {} ".format(icao),TO_DEBUG)
                    ac_data = { 'tail' : row[4], 'icao_hex' : icao , 'man' : None ,  'model' : row[5] }
                    self.insert(ac_data)
                    inserts = inserts + 1

                counter=counter+1
                if not(counter % 50000):
                    loggit("modeS {} records. {} inserts , {} updates {} errors \r".format(counter,inserts,updates,errors),TO_SCREEN)       
                    # print(".",end='',flush=True)
                    self.handle.commit()
            except Exception as e:
                loggit("error parsing in modeS.tsv {} tsv is {} ".format(e,row),TO_FILE)

        loggit("\nfinished parsing ModeS tsv {} records. {} inserts , {} updates {} errors ".format(counter,inserts,updates,errors))       

        self.handle.commit()


    def update_from_adsbex_basic_data(self):
        counter = 0
        inserts=0
        updates=0
        errors=0
        loggit("update from ADSB Exchange Basic data")
        with open('basic-ac-db.json') as f:
            while True:
                try:
                    counter = counter + 1
                    line = f.readline()
                    if not line:
                        break
                    ac = json.loads(line)
                    icao = ac["icao"].lower()
                    local_data = self.lookup(icao,False)
                    ac_data = { 'tail' : ac["reg"], 'icao_hex' : icao , 'man' : ac["manufacturer"], 'model' : ac["icaotype"] }
                
                    if local_data is None:
                        # missing data - so insert it
                        self.insert(ac_data)
                        inserts = inserts + 1

                    if not(counter % 50000):
                        loggit("interim {} records. {} inserts , {} updates {} errors \r".format(counter,inserts,updates,errors),BOTH) 
                        # print(".",end='',flush=True)
                        self.handle.commit()
                except Exception as e:
                    loggit("error parsing in basic-ac-db.json {} json is {} ".format(e,line),TO_FILE)
                    errors = errors + 1                  
            loggit("\nfinished parsing basic-ac-db.json {} records. {} inserts , {} updates {} errors ".format(counter,inserts,updates,errors))       
        # commit the changes / insertions we made
        self.handle.commit()
        
    def check_from_adsbex_basic_data(self):
        counter = 0
        errors=0
        records_found=0
        loggit("check  from ADSB Exchange Basic data")
        with open('basic-ac-db.json') as f:
            while True:
                try:
                    counter = counter + 1
                    line = f.readline()
                    if not line:
                        break
                    ac = json.loads(line)
                    icao = ac["icao"].lower()
                    local_data = self.lookup(icao,False)
                                    
                    if local_data is not None:
                       records_found = records_found + 1
                    else:
                        loggit(f"did not find icao {icao}",BOTH)

                    if not(counter % 50000):
                        loggit("interim {} records {} records found {} errors \r".format(counter,records_found,errors),BOTH) 
                        loggit(f"{ac}",BOTH)
                        # print(".",end='',flush=True)
                        self.handle.commit()
                except Exception as e:
                    loggit("error parsing in basic-ac-db.json {} json is {} ".format(e,line),TO_FILE)
                    errors = errors + 1                  
            loggit("\nfinished parsing basic-ac-db.json {} records. {} records found, {} errors ".format(counter,records_found,errors))       
        # commit the changes / insertions we made
   
    def update_from_aircraftDatabase(self):
        counter = 0
        inserts=0
        updates=0
        errors=0
        records_found = 0
        the_same = 0
        loggit("update from aircraft Database ")
        with open('aircraftDatabase.csv') as f:
            my_reader = csv.DictReader(f)
            
            for row in my_reader:
                icao = row["icao24"]
                tail = row['registration']
                plane_type = row['typecode']
                local_data = self.lookup(icao,False)
                counter = counter + 1
                if local_data is None:
                    # No local data , so insert this data
                    self.insert({ 'tail' : tail, 'icao_hex' : icao, 'model' : plane_type })
                    inserts = inserts + 1 
                    records_found = records_found + 1
                else:
                    if local_data[TAIL] == tail and local_data[TYPE] == plane_type:
                        the_same = the_same + 1
                    else:
                        #print(f"different {icao}  {tail} {plane_type} : {local_data}")
                        #print(f"    {row}")
                        if local_data[TAIL] != tail:
                            #print(f"****TAILS**** different {icao}  {tail} {plane_type} : {local_data}")
                            #print(f"    {row}")
                            pass 
                        else:
                            if local_data[TAIL] == ''  and local_data[TYPE]== '': #if we have null data for both then use the new data
                                self.update({ 'tail' : tail, 'icao_hex' : icao, 'model' : plane_type })
                                updates = updates + 1
                                print(f"updated {icao} {tail} {plane_type}")
                if not(counter % 50000):
                        loggit("interim {} records {} records found {} errors \r".format(counter,records_found,errors),BOTH) 
                        # print(".",end='',flush=True)
                        self.handle.commit()
       
        self.handle.commit()
        loggit(f"\nfinished parsing aircraftDatabase.csv  {counter} records: identical  {the_same} inserts {inserts} , updates {updates}   errors {errors} ") 

                
    def update_from_adsb_basestation_data(self):
        loggit("update from BaseStation data")
        handle = sqlite3.connect("BaseStation.sqb")
        cursor = handle.cursor()
        cursor.execute("SELECT ModeS,Registration,ICAOTypeCode FROM Aircraft")
        counter = 0
        inserts=0
        updates=0
        errors=0
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            counter = counter + 1
            icao = row[0]
            tail = row[1]
            plane_type = row[2]
            local_data = self.lookup(icao,False)
            if local_data is None:
                # missing data - so insert it
                self.insert({ 'tail' : tail, 'icao_hex' : icao, 'model' : plane_type })
                inserts = inserts + 1 
            else:
                if local_data[TAIL] != tail or local_data[TYPE] != plane_type:
                    # update the record
                    if tail is not None:
                        loggit("Basestation data {} local {} standing {}".format(icao,local_data,row),TO_DEBUG)
                        self.update({ 'tail' : tail, 'icao_hex' : icao, 'model' : plane_type })
                        updates = updates + 1
            if not(counter % 50000):
                loggit("interim {} records. {} inserts , {} updates {} errors \r".format(counter,inserts,updates,errors),TO_SCREEN)       
                # print(".",end='',flush=True)
                self.handle.commit()
        loggit("\nfinished parsing StandingData  {} records. {} inserts , {} updates {} errors ".format(counter,inserts,updates,errors)) 
        self.handle.commit()

    def update_local_cache(self):
        self.update_from_aircraftDatabase()
        self.update_from_adsbex_basic_data()
        # self.update_from_adsb_basestation_data()
        # self.update_from_modeS_tsv()

    def planespotters(self,hex):
        headers = { 'Accept-Language' : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8", 
            'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36" }
        url = "https://www.planespotters.net/hex/" + hex
        print(f"URL {url}")
        resp = requests.get(url, headers=headers, timeout=30)
        page= resp.text
        print(f"{page}")
        print(f"response code {resp.status_code}")
        soup = BeautifulSoup(page,"html.parser")
        try : 
           div = soup.find("div" ,{"class" : "grid-2"})
           loggit(f"OK {div}")
        except: 
           print("dead")




if __name__ == "__main__":
    init_loggit("normal.txt","/tmp/normal_debug.txt","/tmp/vrs_logging.txt")
    print("Lets start testing")
    home = os.path.expanduser('~/planes/mk2')
    home = '.'
    ds = DataService(home + "/consolidated_data.sqb")
    #ds.lookup('cecedf')

    #ds.update_from_aircraftDatabase()
    #ds.check_from_adsbex_basic_data()
    #ds.update_local_cache()
    ds.planespotters("4CAE6B")

