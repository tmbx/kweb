#!/bin/sh

# change lighttpd main listened to port

set -e

if [ "$#" != "1" ]
then
	echo "Usage: $0 <port>"
	exit 1
fi
PORT="$1"

if [ ! -w "/etc/lighttpd/lighttpd.conf" ]
then
	echo "File /etc/lighttpd/lighttpd.conf is not writable..."
	exit 1
fi


TMPFILE=`mktemp /tmp/conf.XXXXXX`
cp -a /etc/lighttpd/lighttpd.conf $TMPFILE
cat $TMPFILE \
	| sed "s/.*server\.port.*/server.port = $PORT/g" \
	> /etc/lighttpd/lighttpd.conf

