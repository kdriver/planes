import sqlite3

try:
        conn_base = sqlite3.connect('basestation/BaseStation.sqb')
        print("connected to BaseStation")
except Exception as e: 
	print (e)
	exit()


def get_reg(hex_id):
        try:
            ms = hex_id.strip().upper()
            print(ms)
            command=  "SELECT Registration  FROM Aircraft WHERE ModeS='{0}'".format(ms)
            print("the_command {0} \n".format(command) )
            answer = conn_base.execute(command )
            txt = answer.fetchone()
            if txt != None:
                x =  "{0}".format(txt[0])
                return x 
        except Exception as e:
            print("get_reg - flight {0} database exception {1} ".format(hex_id,e) )


def get_plane(hex_id):
        try:
            ms = hex_id.strip().upper()
            print(ms)
            command=  "SELECT Manufacturer,Type  FROM Aircraft WHERE ModeS='{0}'".format(ms)
            print("the_command {0} \n".format(command) )
            answer = conn_base.execute(command )
            txt = answer.fetchone()
            if txt != None:
                x =  "{0}:{1}".format(txt[0],txt[1])
                y = x.split('/')
                answer  = y[0] 
                return answer 
        except Exception as e:
            print("get_plane - flight {0} database exception {1} ".format(hex_id,e) )



h="03c580"
print(get_plane(h))
print(get_reg(h))
