#!/bin/sh
echo "Update reference data"

update_aircraft_data () {
    start_time=$(date +%s)
	echo "\nUpdate $1 , $2"
	# download file if remote file modified date is newer than local file date
	wget  -N  -o /tmp/wget.log $2 
	grep  Omitting /tmp/wget.log > /dev/null
	if [ $? -eq 1 ] ; then
		case $1 in
			*"gz"*)
				echo "Downloaded .. gunzipping $1"
				gunzip -f --keep  $1
				;;
			*"zip"*)
				echo "Downloaded .. unzipping $1"
				unzip -oj $1
				;;
		esac
		echo "decompression done"
	else
		echo "Omitted Download of $1"
	fi
    end_time=$(date +%s)
    elapsed=$(( end_time - start_time ))
    echo "Update took  $elapsed  seconds "
		
} 


update_aircraft_data basic-ac-db.json.gz  http://downloads.adsbexchange.com/downloads/basic-ac-db.json.gz

update_aircraft_data routes.tsv.gz  http://data.flightairmap.com/data/routes.tsv.gz

update_aircraft_data modes.tsv.gz   http://data.flightairmap.com/data/modes.tsv.gz 

update_aircraft_data  BaseStation.sqb.gz http://data.flightairmap.com/data/basestation/BaseStation.sqb.gz

update_aircraft_data  StandingData.sqb.gz http://www.virtualradarserver.co.uk/Files/StandingData.sqb.gz

update_aircraft_data  aircraftDatabase.zip https://opensky-network.org/datasets/metadata/aircraftDatabase.zip

exit 0

