import socket
import time
import struct
import sys
import subprocess as sp
import os
import LED
from multiprocessing import Process
import json

SERVER_ADD = '192.168.4.1'

up_time_cmd = 'ifconfig | grep wlan0'

def wifi_connect(wifi_name, wifi_pwd):
    LED.rgboff()
    blink_process = Process(target=LED.greenblink)
    blink_process.start()
    
    wifi_connect_count = 0
    if wificred['ssid'] == None:
        wifi_connect_count = 999
    valid_connection = False
    while not valid_connection and wifi_connect_count < 5:
        print('wap2lan: attempt %d for wifi' % wifi_connect_count)
        if wifi_connect_count == 0:
            sp.call(['nmcli', "connection", "down", "hotspot"])
            sp.call(['nmcli', "radio", "wifi", "off"])
            sp.call(['nmcli', "radio", "wifi", "on"])
            sp.call(['nmcli', "device", "wifi", "rescan"])
            time.sleep(5)
            sp.call(["sudo", "nmcli", "dev", "wifi", "connect", str(wifi_name), "password", str(wifi_pwd), 'ifname', 'wlan0'])
            time.sleep(5)
            valid_connection = testInternet()

        elif wifi_connect_count <= 3:
            sp.call(["sudo", "nmcli", "dev", "wifi", "connect", str(wifi_name), "password", str(wifi_pwd), 'ifname', 'wlan0'])
            time.sleep(5)
            valid_connection = testInternet()

        else: # give up, leave hotspot running
            sp.call(['nmcli', 'con', 'delete', str(wifi_name)])
            LED.rgboff()
            LED.redOn()
            time.sleep(5)
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
    sp.call(["nmcli", "device", "wifi", "hotspot", "con-name", "hotspot", "ssid", id, "band", "bg",
             "password", "canyouhearme"])
    sp.call(["nmcli", "connection", "modify", 'hotspot', "ipv4.addresses", "192.168.4.1/24"])

def check_up_time():
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
        socket.setdefaulttimeout(20)
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
    time.sleep(5)
    sp.call(["nmcli", "connection", "up", "hotspot"])
    wifi_connect(wificred['ssid'], wificred['password'])
