#!/bin/sh
echo "Update reference data"
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
		echo "\nBasestation.sqb.gz  It hasnt been updated so do nothing "
	fi
else
	echo "File Basestation.sqb.gz doesnt exist - redownload it "
	curl -o BaseStation.sqb.gz http://data.flightairmap.com/data/basestation/BaseStation.sqb.gz  && gunzip  -f --keep BaseStation.sqb.gz
	touch -d "@$trem" ./BaseStation.sqb.gz
fi
remote=`curl --silent --head  http://data.flightairmap.com/data/modes.tsv.gz  | grep Last | sed -e 's/Last-Modified://'`
trem=`date --date="$remote" +%s`
if test -f ./modes.tsv.gz ; then
	echo "file  modes.tsv.gz exists"
	loc=`stat -c %y "modes.tsv.gz"`
	tloc=`date --date="$loc" +%s`
	echo  "local  ${tloc}",`date -d@$tloc`
	echo  "remote ${trem}",`date -d@$trem`
	if [ $(($tloc)) -lt $(($trem)) ] ; then 
		echo "Download it "
		echo "remote $remote"
		echo "local $loc"
		curl -o modes.tsv.gz http://data.flightairmap.com/data/modes.tsv.gz  
		echo "unzip it"
		gunzip -f --keep modes.tsv.gz
		cat modes.tsv | tr '' '_' > /tmp/modes ; cp /tmp/modes ./modes.tsv
		touch -d "@$trem" ./modes.tsv.gz
	else
		echo "\nmodes.tsv.gz It hasnt been updated so do nothing "
	fi
else
	echo "File modes.tsv.gz doesnt exist - redownload it "
	curl -o modes.tsv.gz http://data.flightairmap.com/data/modes.tsv.gz  && gunzip  -f --keep modes.tsv.gz
	cat modes.tsv | tr '' '_' > /tmp/modes ; cp /tmp/modes ./modes.tsv
	touch -d "@$trem" ./modes.tsv.gz
fi
remote=`curl --silent --head  http://data.flightairmap.com/data/routes.tsv.gz  | grep Last | sed -e 's/Last-Modified://'`
trem=`date --date="$remote" +%s`
if test -f ./routes.tsv.gz ; then
	echo "file  routes.tsv.gz exists"
	loc=`stat -c %y "routes.tsv.gz"`
	tloc=`date --date="$loc" +%s`
	echo  "local  ${tloc}",`date -d@$tloc`
	echo  "remote ${trem}",`date -d@$trem`
	if [ $(($tloc)) -lt $(($trem)) ] ; then 
		echo "Download it "
		echo "remote $remote"
		echo "local $loc"
		curl -o routes.tsv.gz http://data.flightairmap.com/data/routes.tsv.gz  
		echo "unzip it"
		gunzip -f --keep routes.tsv.gz
		cat routes.tsv | tr '' '_' > /tmp/routes ; cp /tmp/routes ./routes.tsv
		touch -d "@$trem" ./routes.tsv.gz
	else
		echo "\nroutes.tsv.gz It hasnt been updated so do nothing "
	fi
else
	echo "File routes.tsv.gz doesnt exist - redownload it "
	curl -o routes.tsv.gz http://data.flightairmap.com/data/routes.tsv.gz  && gunzip  -f --keep routes.tsv.gz
	cat routes.tsv | tr '' '_' > /tmp/routes ; cp /tmp/routes ./routes.tsv
	touch -d "@$trem" ./routes.tsv.gz
fi
exit 0
url='http://data.flightairmap.com/data/routes.tsv.gz'
file='routes.tsv.gz'
remote=`curl --silent --head  $url  | grep Last | sed -e 's/Last-Modified://'`
trem=`date --date="$remote" +%s`
if ! test -f $file ; then
	echo "File routes.tsv.gz doesnt exist - redownload it "
	curl -o $file  $url   && gunzip  -f --keep $file
	touch -d "@$trem" $file 
fi
	echo "file  $file "
	loc=`stat -c %y $file
	tloc=`date --date="$loc" +%s`
	echo  "local  ${tloc}",`date -d@$tloc`
	echo  "remote ${trem}",`date -d@$trem`
	if [ $(($tloc)) -lt $(($trem)) ] ; then 
		echo "Download it "
		echo "remote $remote"
		echo "local $loc"
		curl -o $file  $url
		echo "unzip it"
		gunzip -f --keep $file
		touch -d "@$trem" $file
	else
		echo "\nroutes.tsv.gz It hasnt been updated so do nothing "
	fi

