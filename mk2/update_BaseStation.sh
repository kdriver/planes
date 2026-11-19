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

# OpenSky's live metadata API is gone (HTTP 410), and aircraftDatabase.zip stopped
# updating in 2024. The current data is published as dated snapshots, e.g.
# aircraft-database-complete-2025-08.csv - pick the newest one listed.
OPENSKY_S3=https://s3.opensky-network.org/data-samples
opensky_latest=$(wget -q -O - "$OPENSKY_S3?prefix=metadata/aircraft-database-complete-&list-type=2" \
	| grep -o 'metadata/aircraft-database-complete-[0-9-]*\.csv' | sort | tail -1)
if [ -n "$opensky_latest" ] ; then
	opensky_file=$(basename "$opensky_latest")
	if [ ! -f "$opensky_file" ] ; then
		# snapshots never change once published, so only fetch a new name
		echo "\nDownloading new OpenSky aircraft database $opensky_file"
		if wget -q -O "$opensky_file.part" "$OPENSKY_S3/$opensky_latest" ; then
			mv "$opensky_file.part" "$opensky_file"
			touch "$opensky_file"   # so the index rebuild below sees it as new
			ln -sf "$opensky_file" opensky-aircraft-database.csv
			# drop older snapshots (~100MB each)
			for old in aircraft-database-complete-*.csv ; do
				[ "$old" != "$opensky_file" ] && rm -f "$old"
			done
		else
			rm -f "$opensky_file.part"
			echo "OpenSky download failed"
		fi
	else
		echo "OpenSky aircraft database $opensky_file is current"
	fi
else
	echo "Could not find the latest OpenSky aircraft database"
fi

# rebuild the local hex -> tail index if either source is newer than it
if [ ! -f reference_index.sqb ] || [ basic-ac-db.json -nt reference_index.sqb ] || [ opensky-aircraft-database.csv -nt reference_index.sqb ] ; then
	echo "Rebuilding reference index"
	python3 build_reference_index.py
else
	echo "Reference index up to date"
fi

exit 0

