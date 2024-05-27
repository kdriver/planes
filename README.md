# planes
A repository of scripts to process the Flightaware JSON file /var/run/dump1090-fa/aircraft.json 

run 
> python3 detect.py

detect.py needs to be modified for home[]

API tokens are needed for :

Twitter - scripts will tweet planes that pass closer than 2 miles overhead from home ( as defined in detect.py lat/lon ) 
* supply twittertokens.py

ADSBExchange  - look up plane data not available locally from databases
* supply ADSBExKey.py


Lookups are made to blackswan,Openstreetmap

The scripts will download  Basestation / ModeS / StandingData to help enrich plane data.

Local data is created in :

* planes.sqb   .. all planes passing within 50 miles of home
* adsb_cache.sqb .. any lookup from adsb exchange is cached to prevent further lookups
* unknown_planes.sqb  - planes where no enrichment is found
* vrs_data.sqb  -   maximum distances at 10k, 20k, and unlimited heights

kmz files are created for each plane in subdirectory kmls  - initially a short while after passing the closest point, then when track expires, the whole track.

python3 splat.py produces splat_10k , 20k , max kmz files to show max distances from home  ( uses vrs_data.sqb ) 
