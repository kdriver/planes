#!/bin/sh
remote=`curl --silent --head  http://data.flightairmap.com/data/basestation/BaseStation.sqb.zip  | grep Last | sed -e 's/Last-Modified://'`
trem=`date --date="$remote" +%s`
if test -f ./BaseStation.sqb.zip ; then
	echo "file  BaseStation.sqb.zip exists"
	loc=`stat -c %z "BaseStation.sqb.zip"`
	tloc=`date --date="$loc" +%s`
	echo  "local  ${tloc}",`date -d@$tloc`
	echo  "remote ${trem}",`date -d@$trem`
	if [ $(($tloc)) -lt $(($trem)) ] ; then 
		echo "Download it "
		echo "remote $remote"
		echo "local $loc"
		curl -o BaseStation.sqb.zip http://data.flightairmap.com/data/basestation/BaseStation.sqb.zip  
		echo "unzip it"
		unzip BaseStation.sqb.zip
		touch -d "@$trem" ./BaseStation.sqb.zip
	else
		echo "It hasnt been updated so do nothing "
	fi
else
	echo "File doesnt exist - redownload it "
	curl -o BaseStation.sqb.zip http://data.flightairmap.com/data/basestation/BaseStation.sqb.zip  && unzip -o BaseStation.sqb.zip
	touch -d "@$trem" ./BaseStation.sqb.zip
fi
exit 0
