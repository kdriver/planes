#!/bin/sh
remote=`curl --silent --head  http://data.flightairmap.com/data/basestation/BaseStation.sqb.gz  | grep Last | sed -e 's/Last-Modified://'`
trem=`date --date="$remote" +%s`
if test -f ./BaseStation.sqb.gz ; then
	echo "file  BaseStation.sqb.gz exists"
	loc=`stat -c %y "BaseStation.sqb.gz"`
	tloc=`date --date="$loc" +%s`
	echo  "local  ${tloc}",`date -d@$tloc`
	echo  "remote ${trem}",`date -d@$trem`
	if [ $(($tloc)) -lt $(($trem)) ] ; then 
		echo "Download it "
		echo "remote $remote"
		echo "local $loc"
		curl -o BaseStation.sqb.gz http://data.flightairmap.com/data/basestation/BaseStation.sqb.gz  
		echo "unzip it"
		gunzip -f --keep BaseStation.sqb.gz
		touch -d "@$trem" ./BaseStation.sqb.gz
	else
		echo "It hasnt been updated so do nothing "
	fi
else
	echo "File doesnt exist - redownload it "
	curl -o BaseStation.sqb.gz http://data.flightairmap.com/data/basestation/BaseStation.sqb.gz  && gunzip  -f --keep BaseStation.sqb.gz
	touch -d "@$trem" ./BaseStation.sqb.gz
fi
exit 0
