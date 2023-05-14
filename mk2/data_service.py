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
            self.handle.commit()
            self.black_counter = 0
            self.counter= 0
            self.icao_map = ICAOCountries()
            self.suppress_dict = {}
            self.start_time=datetime.now()
            # self.refresh_external_data()
            # self.update_local_cache()
        except Exception as my_e:
            print(my_e)
            print(f"Could not open database {data_file}")
            sys.exit(1)

    def update_the_cache(self):
        self.update_local_cache()

    def call_command(self, command):
        txt = subprocess.check_output(command, stderr=subprocess.STDOUT)
        if isinstance(txt, bytes):
            val = txt.decode('utf-8')
        else:
            val = txt

        loggit(val)

        return val

    def blackswan_lookup(self,icao):
        if '~' in icao:
            loggit("~ detected in icao - dont lookup in blackswan" )
            return(None,None)

        try:
    
            self.black_counter = self.black_counter + 1
            the_url = f'https://blackswan.ch/aircraft/{icao}'
            loggit(f' {icao} in blackswan {the_url}')

            r = requests.get(the_url)
            page= r.text
            soup = BeautifulSoup(page,"html.parser")
            reg = soup.find("td" ,attrs={"data-target" :"reg"})
            #model = soup.find("td" ,attrs={"data-target" :"model"}).text
            model = soup.find("td" ,attrs={"data-target" :"type"})
            the_diff = datetime.now() - self.start_time
            in_seconds = the_diff.total_seconds()
            in_days = in_seconds/(60*60*24)
            requests_per_day = self.black_counter/in_days
            loggit(f"{self.black_counter} requests total, which is {requests_per_day} per day after {in_days} days") 

            if reg is None or model is None:
                loggit(f"blackswan has no data for {icao}")
                return(None,None)
            
            regt = reg.text
            modelt = model.text
            return (regt,modelt)
        except Exception as my_e:
            loggit(f'could not find plane  {icao} in blackswan , exception : {my_e}')
            return (None,None)

    def get_country(self, icao):
        return self.icao_map.icao_to_country(icao)
    
    def flush_suppress_list(self):
        """  Flush the list that caches the icoa to prevent too many API lookups """
        now = time.time()
        if len(self.suppress_dict) > 0:
            loggit(f"suppress list :")
        delete_list = []
        for plane in self.suppress_dict.items():
            k,value = plane
            age = now - value
            loggit(f"   suppress list  {k}, seconds old {age}, hours old {age/3600} hours")
            if age > float(60*60*24):
                delete_list.append(k)
        
        for item in delete_list:
            loggit(f"flush suppress list for {item}",BOTH)
            del self.suppress_dict[item]
            
    
    def is_suppressed(self,icao):
        if icao in self.suppress_dict:
            return True
        return False
    
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

            loggit(f"remote lookup {the_hex}",BOTH)
            try:
                adsb = adsbex_query.adsb_lookup(the_hex)
            except Exception as my_exception:
                loggit(f"adsb lookup exception {my_exception}", BOTH)
                adsb = None

            if adsb is not None and adsb['tail'] !='CONTACTADSBX':
                loggit(f"{adsb}",BOTH)
                row = (adsb['tail'], adsb['type'])
                loggit(f"{the_hex} found {row} in from ADSB API",BOTH)
                data = {
                        'tail' : adsb['tail'],
                        'model' : adsb['type'],
                        'icao_hex' : the_hex,
                        'man' : None
                        }
                loggit(f"adsb exchange lookup {data}", BOTH)
                self.insert(data,True)
                return row
            loggit(f"{icao} Not found in ADSB exchange API",BOTH)
            try:
                blackswan = self.blackswan_lookup(the_hex)
                if blackswan[0] is not None:
                    row = (blackswan[0], blackswan[1])
                    data = {
                                'tail' : blackswan[0],
                                'model': blackswan[1],
                                'icao_hex' : the_hex,
                                'man' : None
                            }
                    loggit(f"{the_hex} found {row} from blackswan API",BOTH)
                    if blackswan[0] != '':
                        self.insert(data,True)
                        return row
                loggit(f"{icao} Not found in blackswan API",BOTH)
                self.suppress_dict[icao] = time.time();

            except Exception as e_name:
                loggit(f"blackswan lookup exception {e_name}", BOTH)
           
        except Exception as e_name:
            loggit(f"error looking up {icao} {e_name}", TO_FILE)
        return None

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
                            b=1
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



if __name__ == "__main__":
    init_loggit("normal.txt","/tmp/normal_debug.txt")
    print("Lets start testing")
    home = os.path.expanduser('~/planes/mk2')
    home = '.'
    ds = DataService(home + "/consolidated_data.sqb")
    #ds.lookup('cecedf')

    #ds.update_from_aircraftDatabase()
    #ds.check_from_adsbex_basic_data()
    ds.update_local_cache()
