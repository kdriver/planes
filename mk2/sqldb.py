import sqlite3


create_text = """ CREATE TABLE IF NOT EXISTS planes ( id integer primary key autoincrement, ts date,flight text, hex text, tail text, plane text,alt  integer, track float, nearest_point float, lat  float, long float ); """ 
cols = " ts, flight, hex , tail , plane, alt ,  track , nearest_point , lat  , long   " 

sql_conn=0

def attach_sqldb():
    global sql_conn
    try:
        sql_conn = sqlite3.connect("planes.sqb")
        cur = sql_conn.cursor()
        cur.execute(create_text)
        sql_conn.commit()
        print("conneted to sqlite planes.sqb database ok\n")
    except Exception as e:
        print(e)

def insert_data(data_tuple):
        global sql_conn
        try:
            cur = sql_conn.cursor()
            cur.execute("INSERT INTO planes(%s) VALUES (?,?,?,?,?,?,?,?,?,?)" % cols,data_tuple)
            sql_conn.commit();
        except :
            pass
            #print(e)




