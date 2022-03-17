# planes
A repository of scripts to process the Flightaware JSON file /var/run/dump1090-fa/aircraft.json 

run by python3 detect.py

API tokens are needed for :

Twitter - scripts will tweet planes that pass closer than 2 miles overhead from home ( as defined in detect.py lat/lon ) 
ADSBExchange  - look up plane data not acvailable locally from databases

Lookups are made to blackswan,Openstreetmap

The scripts will download  Basestation / ModeS / StandingData to help enrich plane data.

Local data is created in :

planes.sqb   .. all planes passing within 50 miles of home
adsb_cache.sqb .. any lookup from adsb exchange is cached to prevent further lookups
unknown_planes.sqb  - ones where no enrichment is found

kmz files are created for each plane 
