import sqlite3


try:
	conn = sqlite3.connect('StandingData.sqb')
	print("connected")
except Exception as e: print (e)


answer = conn.execute("SELECT FromAirportName,ToAirportName  FROM RouteView WHERE Callsign = '%s'" % 'CFE229X' )


txt = answer.fetchone()

if txt != None:
	print("%s -> %s" % txt ) 

