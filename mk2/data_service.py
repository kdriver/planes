"""   A module to provide enrichment services from reference data downloaded externally to this module """

import os
import sqlite3
import csv
import subprocess
import json
import sys

import adsbex_query

from add_to_unknown import blackswan_lookup as blackswan_lookup

from loggit import loggit
from loggit import TO_FILE, TO_SCREEN, BOTH, TO_DEBUG

# Tuple index
TAIL = 0
TYPE = 1



class DataService:
    """
    This class manages access to reference data so that 
    we can use the icao hex value to lookup tail, plane etc
    """
    create_text = """ CREATE TABLE IF NOT EXISTS aircraft ( id integer primary key autoincrement,  hex text, tail text,type text , seen integer, looked_up integer); """
    cols = "  hex , tail , type , seen  , looked_up"

    def __init__(self, data_file):
        try:
            self.create_text = """ CREATE TABLE IF NOT EXISTS aircraft ( id integer primary key autoincrement,  hex text, tail text,type text , seen integer, looked_up integer); """
            self.cols = "  hex , tail , type , seen  , looked_up"
            self.handle = sqlite3.connect(data_file)
            cursor = self.handle.cursor()
            cursor.execute(self.create_text)
            self.handle.commit()
            # self.refresh_external_data()
            # self.update_local_cache()
        except Exception as e:
            print(e)
            print("Could not open database {}".format(data_file))
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


    def lookup(self, icao, remote_lookup=True):
        # loggit("lookup {}".format(icao),BOTH)
        """
        Look for data against the icao hex value and return a list of va,ues found, or None
        """
        try:

            the_hex = icao.lower()

            if '~' in the_hex:  # Its a TIS-B record
                return None
            rows = self.handle.execute(
                "SELECT tail,type FROM aircraft WHERE hex = ?", (the_hex,))
            row = rows.fetchone()
            if row is not None:
                # loggit("{} found {} in consolidated data".format(the_hex,row),BOTH)
                return row

            if remote_lookup is not True:
                return None

            loggit("remote lookup {}".format(the_hex),BOTH)
            try:
                adsb = adsbex_query.adsb_lookup(the_hex)
            except Exception as my_exception:
                loggit("adsb lookup exception {}".format(my_exception), BOTH)
                adsb = None

            if adsb is not None:
                row = (adsb['tail'], adsb['type'])
                loggit("{} found {} in from ADSB API".format(the_hex,row),BOTH)
                data = {
                        'tail' : adsb['tail'],
                        'model' : adsb['type'],
                        'icao_hex' : the_hex,
                        'man' : None
                        }
                loggit("adsb exchange lookup {}".format(data), BOTH)
                self.insert(data,True)
                return row
            loggit("{} Not found in ADSB exchange API".format(icao),BOTH)
            try:
                blackswan = blackswan_lookup(the_hex)
                if blackswan[0] is not None:
                    row = (blackswan[0], blackswan[1])
                    data = {
                                'tail' : blackswan[0],
                                'model': blackswan[1],
                                'icao_hex' : the_hex,
                                'man' : None
                            }
                    loggit("{} found {} in from blackswan API".format(the_hex,row),BOTH)
                    self.insert(data,True)
                    return row
                loggit("{} Not found in blackswan API".format(icao),BOTH)

            except Exception as e:
                loggit("blackswan lookup exception {}".format(e), BOTH)
           
        except Exception as e:
            loggit("error looking up {} {}".format(icao, e), TO_FILE)
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
        modes_file = open("./modes.tsv")
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
                    """
		    Dont use this data as he master reference - it seemslike mostly StandingData and Blackswan agree where there is a difference, so this must be less reliable
                    else:
                        # if local_data[TAIL] != ac_data["tail"] or local_data[TYPE] != ac_data["model"]:
			#   only update the data if the tail number is different. Otherwise we end up changing for the sake of it.
                        if local_data[TAIL] != ac_data["tail"]:
                            loggit("Basic Data tail diff {} local {} standing {}".format(icao,local_data,ac_data),TO_DEBUG)
                            # update the record
                            self.update(ac_data)
                            updates = updates + 1
                    """

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
        self.update_from_adsbex_basic_data()
        # self.update_from_adsb_basestation_data()
        # self.update_from_modeS_tsv()



if __name__ == "__main__":
    print("Lets start testing")
    home = os.path.expanduser('~/planes/mk2')
    ds = DataService(home + "/consolidated_data.sqb")
    ds.update_local_cache()
