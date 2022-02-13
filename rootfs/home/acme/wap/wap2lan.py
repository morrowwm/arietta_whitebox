'''
This script is started at boot time. It checks if the internet can be reached, and it not, puts the machine into WAP mode.
As a WAP, the device uses credentials hardcoded below in the create_hotspot() method.
From a device with wifi, connect to the hotspot, and setup the network.
That can be done using nmcli directly. Or create a file /etc/mynetwork.json with your wifi credentials. There is a template beside this script.
It should contain
    {"ssid":"mynetwork","password":"mypassword"}
Then rerun the script or reboot, and the script will create the network connection.

Use
    journalctl -u wap2lan.service
to troubleshoot.
When the script is running the carrier board LED will light to indicate what is happening.
    red - can't see the internet
    flashing green - trying the network credentials
    green: on the network
    or
    blue: staying as WAP with IP address 192.168.4.1
So don't try ssh until you see solid green or blue.

use
   sudo systemctl disable wap2lan.service # to disable the script
   sudo systemctl start wap2lan.service # to run
   sudo systemctl enable wap2lan.service # to reenable
'''
import socket
import time
import struct
import sys
import subprocess as sp
import os
import LED
from multiprocessing import Process
import json

def wifi_connect(wifi_name, wifi_pwd):
    LED.rgboff()
    blink_process = Process(target=LED.greenblink)
    blink_process.start()
    
    wifi_connect_count = 0
    if wificred['ssid'] == None:
        wifi_connect_count = 999
    valid_connection = False
    while not valid_connection and wifi_connect_count < 2:
        print('wap2lan: attempt %d for wifi' % wifi_connect_count)
        if wifi_connect_count == 0:
            sp.call(['nmcli', "connection", "down", "hotspot"])
            sp.call(['nmcli', "radio", "wifi", "off"])
            sp.call(['nmcli', "radio", "wifi", "on"])
            sp.call(['nmcli', "device", "wifi", "rescan"])
            time.sleep(2)
            sp.call(["sudo", "nmcli", "dev", "wifi", "connect", str(wifi_name), "password", str(wifi_pwd), 'ifname', 'wlan0'])
            time.sleep(3)
            valid_connection = testInternet()

        elif wifi_connect_count <= 3:
            sp.call(["sudo", "nmcli", "dev", "wifi", "connect", str(wifi_name), "password", str(wifi_pwd), 'ifname', 'wlan0'])
            time.sleep(3)
            valid_connection = testInternet()

        else: # give up, leave hotspot running
            sp.call(['nmcli', 'con', 'delete', str(wifi_name)])
            LED.rgboff()
            LED.redOn()
            time.sleep(3)
            LED.redOff()
            sp.call(['nmcli', "connection", "up", "hotspot"])
            break

        wifi_connect_count = wifi_connect_count + 1

    blink_process.terminate()
    LED.rgboff()
    if valid_connection:
        LED.greenOn()
        # Save network name for the uninstall
        file = open('/etc/networkName', 'w')
        file.write(wifi_name)
        file.close()
    else:
        LED.blueOn()

def create_hotspot():
    id = 'WHITEBOX'
    pwd = 'canyouhearme'
    sp.call(["nmcli", "device", "wifi", "hotspot", "con-name", "hotspot", "ssid", id, "band", "bg",
             "password", pwd])
    sp.call(["nmcli", "connection", "modify", 'hotspot', "ipv4.addresses", "192.168.4.1/24"])

def check_up_time():
    up_time_cmd = 'ifconfig | grep wlan0'
    while True:
        try:
            up_time = sp.check_output(up_time_cmd, shell=True)
            if not up_time == '':
                return
        except:
            time.sleep(10)
            sp.call(['sudo', 'nmcli', 'r', 'wifi', 'on'])
            return

def testInternet():
    try:
        print('wap2lan: Checking connection')
        socket.setdefaulttimeout(10)
        host = socket.gethostbyname('www.google.com')
        s = socket.create_connection((host,80), 2)
        s.close()
        return True
    except Exception as e:
        print(e)
    return False

if __name__ == "__main__":
    check_up_time()
    LED.redOn()
    if testInternet():
        LED.rgboff()
        LED.greenOn()
        sys.exit()

    # network is not up, establish hotspot
    try:
        with open("/etc/mynetwork.json", "r") as jsonfile:
            wificred = json.load(jsonfile)
            print("wap2lan: Read wifi creds: %s %s" % (wificred['ssid'], wificred['password']))
    except IOError:
        print("/etc/mynetwork.json does not exist. Create as ssid, password.")
        wificred = {'ssid': None, 'password': None} 

    if os.path.isfile('/etc/NetworkManager/system-connections/hotspot'):
        sp.call(["sudo", "rm", "/etc/NetworkManager/system-connections/hotspot"])
        sp.call(["nmcli", "connection", "delete", 'hotspot'])
        time.sleep(10)
    create_hotspot()
    sp.call(["nmcli", "connection", "down", "hotspot"])
    time.sleep(3)
    sp.call(["nmcli", "connection", "up", "hotspot"])
    wifi_connect(wificred['ssid'], wificred['password'])
