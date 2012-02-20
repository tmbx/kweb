#!/bin/sh

# add/remove lines to apache2 ports.conf file

set -e

if [ "$#" -lt "2" -o "$#" -gt "3" ]
then
	echo "Usage: $0 (enable|disable) port [host]"
	echo "   ie: $0 enable 8001 192.168.1.1"
	echo "   ie: $0 disable 8001"
	exit 1
fi
action="$1"
port="$2"
host="$3"

if [ "$3" = "" ]; then
	bind="$port"
else
	bind="$host:$port"
fi

if [ ! -w "/etc/apache2/ports.conf" ]
then
	echo "File /etc/apache2/ports.conf is not writable..."
	exit 1
fi

case $action in
	"enable")
		if ! grep "\s*Listen\s*$bind$" /etc/apache2/ports.conf >/dev/null 2>&1
		then
			echo "Listen $bind" >> /etc/apache2/ports.conf
			echo "port enabled"
		else
			echo "port already enabled"
		fi
		;;
	"disable")
		if ! grep "\s*Listen\s*$bind$" /etc/apache2/ports.conf >/dev/null 2>&1
		then
			echo "already disabled"
		else
			cp -a /etc/apache2/ports.conf /etc/apache2/ports.conf.TMP123456
			cat /etc/apache2/ports.conf.TMP123456 | sed "/^\s*Listen\s*$bind$/d" > /etc/apache2/ports.conf
		fi
		;;
	*)
		echo "invalid command..."
		return 1
		;;
esac


