import json
import os
import sqlite3
import csv
import subprocess

from loggit import loggit
from loggit import TO_FILE,TO_SCREEN,TO_DEBUG

#Tuple index
TAIL=0
TYPE=1

"""
This class manages access to reference data so that we can use the icao hex value to lookup tail, plane etc
"""

class DataService:

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
            #self.refresh_external_data()
            self.update_local_cache()
        except Exception as e:
            print(e)
            print("Could not open database {}".format(data_file))
            exit(1)

    def call_command(self,command):
        txt = subprocess.check_output(command,stderr=subprocess.STDOUT)
        if isinstance(txt,bytes):
            val = txt.decode('utf-8')
        else:
            val = txt

        loggit(val)

        return val

    """ 
        Look for data against the icao hex value and return a list of va,ues found, or None 
    """        
    def lookup(self,icao):
        try:
          
            rows = self.handle.execute("SELECT tail,type FROM aircraft WHERE hex = ?",(icao.lower(),))
            row = rows.fetchone()
            if row:
                return row
            else:
                return None
        except Exception as e:
            loggit("error looking up {} {}".format(icao,e) ,TO_FILE)
            return None

    def insert(self,plane):
        try:
            cursor = self.handle.cursor()
            data_tuple = ( plane["icao_hex"].lower(), plane["tail"], plane["model"], 0,0 )
            cursor.execute("INSERT INTO aircraft(%s) VALUES (?,?,?,?,?)" % self.cols,data_tuple)
            loggit("insert {} ".format(data_tuple),TO_DEBUG)
            #self.handle.commit()
        except Exception as e:
            print("insert into local cache exception {}".format(e))

        
    
    def update(self,plane):
        try:
            data = ( plane["tail"],plane["model"],plane["icao_hex"].lower() )
            # print(data)
            self.handle.execute("UPDATE aircraft SET tail = ?,type = ? WHERE hex = ? ",data )
        except Exception as e:
            print("update local cache exception {}".format(e))

    def refresh_external_data(self):
        print("Refreshing data from external source")
        self.call_command(["./update_BaseStation.sh"])
        loggit("script returned")

     
    def update_from_adsbex_basic_data(self):
        counter = 0
        inserts=0
        updates=0
        errors=0
        with open('basic-ac-db.json') as f:
            while True:
                try:
                    counter = counter + 1
                    line = f.readline()
                    if not line:
                        break
                    ac = json.loads(line)
                    icao = ac["icao"].lower()
                    local_data = self.lookup(icao)
                    ac_data = { 'tail' : ac["reg"], 'icao_hex' : icao , 'man' : ac["manufacturer"], 'model' : ac["icaotype"] }
                
                    if local_data is None:
                        # missing data - so insert it
                        self.insert(ac_data)
                        inserts = inserts + 1
                    """
		    Dont use this data as he master reference - it seemslike mostly StandingData and Blackswan agree where there is a difference, so this must be less reliable
                    else:
                        #if local_data[TAIL] != ac_data["tail"] or local_data[TYPE] != ac_data["model"]:
			#   only update the data if the tail number is different. Otherwise we end up changing for the sake of it.
                        if local_data[TAIL] != ac_data["tail"]:
                            loggit("Basic Data tail diff {} local {} standing {}".format(icao,local_data,ac_data),TO_DEBUG)
                            # update the record
                            self.update(ac_data)
                            updates = updates + 1
                    """

                    if not(counter % 1000):
                        loggit("interim {} records. {} inserts , {} updates {} errors \r".format(counter,inserts,updates,errors),TO_SCREEN)       
                        # print(".",end='',flush=True)
                        self.handle.commit()
                except Exception as e:
                    loggit("error parsing in basic-ac-db.json {} json is {} ".format(e,line),TO_FILE)
                    errors = errors + 1
                    
            loggit("\nfinished parsing basic-ac-db.json {} records. {} inserts , {} updates {} errors ".format(counter,inserts,updates,errors))       
        # commit the changes / insertions we made
        self.handle.commit()

    def update_from_adsb_standing_data(self):
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
            type = row[2]
            local_data = self.lookup(icao)
            if local_data is None:
                # missing data - so insert it
                self.insert({ 'tail' : tail, 'icao_hex' : icao, 'model' : type })
                inserts = inserts + 1 
            else:
                if local_data[TAIL] != tail or local_data[TYPE] != type:
                    # update the record
                    if tail is not None:
                        loggit("StandingData {} local {} standing {}".format(icao,local_data,row),TO_DEBUG)
                        self.update({ 'tail' : tail, 'icao_hex' : icao, 'model' : type })
                        updates = updates + 1
            if not(counter % 1000):
                        loggit("interim {} records. {} inserts , {} updates {} errors \r".format(counter,inserts,updates,errors),TO_SCREEN)       
                        # print(".",end='',flush=True)
                        self.handle.commit()
        loggit("\nfinished parsing StandingData  {} records. {} inserts , {} updates {} errors ".format(counter,inserts,updates,errors)) 

    def update_local_cache(self):
        self.update_from_adsbex_basic_data()
        self.update_from_adsb_standing_data()



if __name__ == "__main__":
    print("Lets start testing")
    ds = DataService("/tmp/test.db")
