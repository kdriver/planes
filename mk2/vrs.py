import sqlite3
from loggit import loggit
from loggit import ALL,TO_DEBUG
import time

create_text = """ CREATE TABLE IF NOT EXISTS vrs ( 
    id integer primary key autoincrement,  bearing integer, 
    lat_10k float, lon_10k float, alt_10k integer , miles_10k float, the_plane_10k integer, the_time_10k integer,
    lat_20k float, lon_20k float, alt_20k integer , miles_20k float, the_plane_20k integer, the_time_20k integer,
    lat_max float, lon_max float, alt_max integer , miles_max float, the_plane_max integer ,the_time_max integer
    ); """ 
cols = " bearing , lat_10k , lon_10k , alt_10k , miles_10k , the_plane_10k, the_time_10k,\
                   lat_20k , lon_20k , alt_20k , miles_20k , the_plane_20k, the_time_20k,\
                   lat_max , lon_max , alt_max , miles_max , the_plane_max, the_time_max "

class Vrs():
    def __init__(self,dbname):
        self.db  = sqlite3.connect(dbname)
        self.cur = self.db.cursor()
        self.cur.execute(create_text)
        self.db.commit()
        self.the_time = 0
        answer = self.db.execute("SELECT bearing FROM vrs WHERE bearing = 0;")
        txt = answer.fetchone()
        if txt is None:
            # create the template
            for deg in range(0,360,1):
                self.db.execute("INSERT into vrs({}) VALUES ( ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,? )".format(cols),(deg,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0))
            self.db.commit() 
            print("VRS schema and data created")
        else:
            print("VRS data exists")

    def update_entry(self,bearing,lat,lon,alt,miles,icao):
        self.the_time=time.time()
        alarm=""
        if miles > 400.0:
            alarm = " alarm {} ".format(self.the_time)
            loggit(f'bad position found {icao} {vars(self)} {bearing} {lat} {lon} {alt} {miles} {alarm}')
            return

        if alt <= 10000:
            self.update_entry_10k(bearing,lat,lon,alt,miles,icao,alarm)
        else:
            if alt <= 20000:
                self.update_entry_20k(bearing,lat,lon,alt,miles,icao,alarm)
            else:
                self.update_entry_max(bearing,lat,lon,alt,miles,icao,alarm)




    def update_entry_10k(self,bearing,lat,lon,alt,miles,icao,alarm):
        answer = self.db.execute("SELECT miles_10k FROM vrs WHERE bearing ={}".format(bearing))
        txt = answer.fetchone()
        if txt is not None:
            # print("retrieved {}".format(txt[0]))
            if miles > float(txt[0]):
                self.db.execute("UPDATE vrs SET lat_10k = ?, lon_10k = ?, alt_10k = ? , miles_10k = ?, the_plane_10k = ?, the_time_10k = ?  WHERE bearing = {}".format(bearing),(lat,lon,alt,miles,icao,self.the_time))
                self.db.commit()
                loggit("updated 10k {} from {} to {} , with icao {} alt {} {}".format(bearing,txt[0],miles,icao,alt,alarm),ALL-TO_DEBUG)
        else:
            print("no entry for bearing {}".format(bearing))

    def update_entry_20k(self,bearing,lat,lon,alt,miles,icao,alarm):
        answer = self.db.execute("SELECT miles_20k FROM vrs WHERE bearing ={}".format(bearing))
        txt = answer.fetchone()
        if txt is not None:
            # print("retrieved {}".format(txt[0]))
            if miles > float(txt[0]):
                self.db.execute("UPDATE vrs SET lat_20k = ?, lon_20k = ?, alt_20k = ? , miles_20k = ? , the_plane_20k = ? , the_time_20k = ? WHERE bearing = {}".format(bearing),(lat,lon,alt,miles,icao,self.the_time))
                self.db.commit()
                loggit("updated 20k {} from {} to {} , with icao {} alt {} {}".format(bearing,txt[0],miles,icao,alt,alarm),ALL-TO_DEBUG)
        else:
            print("no entry for bearing {}".format(bearing))

    def update_entry_max(self,bearing,lat,lon,alt,miles,icao,alarm):
        answer = self.db.execute("SELECT miles_max FROM vrs WHERE bearing ={}".format(bearing))
        txt = answer.fetchone()
        if txt is not  None:
            # print("retrieved {}".format(txt[0]))
            if miles > float(txt[0]):
                self.db.execute("UPDATE vrs SET lat_max = ?, lon_max = ?, alt_max = ? , miles_max = ? , the_plane_max = ? , the_time_max = ? WHERE bearing = {}".format(bearing),(lat,lon,alt,miles,icao,self.the_time))
                self.db.commit()
                loggit("updated max {} from {} to {} , with icao {} alt {} {}".format(bearing,txt[0],miles,icao,alt,alarm),ALL-TO_DEBUG)
        else:
            print("no entry for bearing {}".format(bearing))


if __name__ == '__main__':
    vserver = Vrs("vrs_test.sqb")
    print("done")
    vserver.update_entry_10k(10,2.0,3.0,1000,24.5)
    vserver.update_entry_10k(10,2.0,3.0,1000,24.6)
    vserver.update_entry_10k(10,2.0,3.0,1000,24.7)
    vserver.update_entry_10k(10,2.0,3.0,1000,24.6)
