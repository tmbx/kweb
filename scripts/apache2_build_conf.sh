#!/bin/sh

# BUILD CONFIG FILES FOR APACHE
# - takes a template file
# - replace some variables
# - put in /etc/apache2/sites-available/<app>

# exit on first error
set -e

if [ "$#" != "5" ]
then
    echo "Usage: $0 <templ> <app> <servername> <virtualhost> <port>"
    echo "   ie: $0 /usr/share/kws-web/config/kws-web.conf kws-web 0 '*' 3001"
	echo "   ie: $0 /usr/share/kws-web/config/kws-web.conf kws-web kas.teambox.co 192.168.200.1 443"
    exit 1
fi

TEMPL="$1"
APP="$2"
SERVERNAME="$3"
VIRTUALHOST="$4"
PORT="$5"


# validation
if [ ! -e "$TEMPL" ]
then
	echo "No template config for application '$APP'."
	exit 1
fi

# "compile" apache config
TMPFILE=`mktemp /tmp/conf.XXXXXX`
cat $TEMPL \
	| sed "s#__SERVERNAME__#$SERVERNAME#g" \
	| sed "s#__VIRTUALHOST__#$VIRTUALHOST#g" \
	| sed "s#__PORT__#$PORT#g" > $TMPFILE
mv $TMPFILE /etc/apache2/sites-available/$APP



