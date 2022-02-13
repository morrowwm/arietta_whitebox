#!/bin/bash

IP=`hostname -I | sed "s/ *$//"`

sed -e "s/IP_ADDR_HERE/${IP}/" /home/acme/eyeserver/client.html > /var/www/html/eye/index.html
