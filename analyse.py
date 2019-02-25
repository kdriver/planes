import sqlite3


try:
    conn = sqlite3.connect("planes.sqb")
except Exception as e:
    print("Exception %s\n"% e)
    exit()

def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d


conn.row_factory = dict_factory

cur = conn.cursor()
cur.execute("SELECT * from planes")

planes=[]
hex_dict = {}
tail_dict = {}
flight_dict = {}
i=0

r = cur.fetchone()
while  r :
    hex_dict[r["hex"]] = 1
    tail_dict[r["tail"]] = 1
    flight_dict[r["flight"]] = 1
    planes.append(r)
    i = i + 1
    r = cur.fetchone()


print (" There were %d records \n"%i)
print (" There were %d hex values \n"%len(hex_dict))
print (" There were %d tail values \n"%len(tail_dict))
print (" There were %d flight values \n"%len(flight_dict))

# which flights does the plane conduct ( by hex ) ?
mode_ss=[]
for mode_s in hex_dict:
    flights=[]
    for event in planes:
        if event["hex"] == mode_s:
            flights.append(event["flight"])
            tail = event["tail"]
    s="%s %s %s " % ( mode_s , tail,  flights)
    mode_ss.append((s))

mode_ss.sort()
for num in mode_ss:
    print(num);

# which flights does the plane conduct ( by tail ) ?
tails=[]
for tail  in tail_dict:
    flights=[]
    for event in planes:
        if event["tail"] == tail and tail != 'n/a' and event["tail"] != 'n/a' and event["tail"] != '0':
            flights.append(event["flight"])
            mode_s = event["hex"]
    s="%s %s %s " % ( tail  , mode_s, flights)
    tails.append((s))

tails.sort()
for tail in tails:
    print(tail);



for mode_s in hex_dict:
    tails={}
    for event in planes:
        if event["hex"] == mode_s:
            tail = event["tail"]
            if  tail != 'n/a':
                tails["tail"] = tail
    if len(tails) > 1 :
        print("%s %s " % ( mode_s  , tails))









