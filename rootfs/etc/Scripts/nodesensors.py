#!/usr/bin/env python

import logging
import pdb
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import bme680
from mpio import ADC
import os
import gc
import subprocess

RED_PATH = """/sys/class/gpio/pioA25/value"""
GREEN_PATH = """/sys/class/gpio/pioA26/value"""
BLUE_PATH = """/sys/class/gpio/pioA27/value"""
EXPORT_CMD = 'echo {0} > /sys/class/gpio/export'
DIRECTION_CMD = 'echo out > /sys/class/gpio/pioA{0}/direction'

data = {}

physicalSensor = bme680.BME680()
physicalSensor.set_humidity_oversample(bme680.OS_2X)
physicalSensor.set_pressure_oversample(bme680.OS_4X)
physicalSensor.set_temperature_oversample(bme680.OS_8X)
physicalSensor.set_filter(bme680.FILTER_SIZE_3)
physicalSensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

physicalSensor.set_gas_heater_temperature(320)
physicalSensor.set_gas_heater_duration(150)
physicalSensor.select_gas_heater_profile(0)

hum_weighting = 0.25

BURN_IN_TIME = 5
TIME_BETWEEN_BURN_INS = 86400

global gas_baseline
global hum_baseline
gas_baseline = 0
hum_baseline = 0

def redOn():
	file = open(RED_PATH, 'w')
	file.write('0')
	file.close()

def greenOn():
	file = open(GREEN_PATH, 'w')
	file.write('0')
	file.close()

def blueOn():
	file = open(BLUE_PATH, 'w')
	file.write('0')
	file.close()

def redOff():
	file = open(RED_PATH, 'w')
	file.write('1')
	file.close()

def greenOff():
	file = open(GREEN_PATH, 'w')
	file.write('1')
	file.close()

def blueOff():
	file = open(BLUE_PATH, 'w')
	file.write('1')
	file.close()

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        global isConnected
        isConnected = True
        print("Connected with result code "+str(rc))
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("environment/crawlspace")
    else:
        print("Connection failed")
        
# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    f = open('received.dat', 'a')
    data = msg.payload.split(",");
    datastr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for datum in data:
        (key, value) = datum.split(":")
        print(key+"="+value)
        datastr += ","+value
    f.write(datastr+"\n")
    print(datastr)
    f.close()

def calculateScore(gas,hum):
    global gas_baseline
    global hum_baseline

    gas_offset = gas_baseline - gas
    hum_offset = hum - hum_baseline
    # Calculate hum_score as the distance from the hum_baseline.
    if hum_offset > 0:
        hum_score = (100 - hum_baseline - hum_offset) / (100 - hum_baseline) * (hum_weighting * 100)
    else:
        hum_score = (hum_baseline + hum_offset) / hum_baseline * (hum_weighting * 100)

    # Calculate gas_score as the distance from the gas_baseline.
    if gas_offset > 0:
        gas_score = (gas / gas_baseline) * (100 - (hum_weighting * 100))
    else:
        gas_score = 100 - (hum_weighting * 100)
    return hum_score + gas_score

    
if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    blueOff()

    # Create paths to LEDs if they don't exist already
    if not os.path.exists(BLUE_PATH):
	    print('Exporting paths')
	    subprocess.call(EXPORT_CMD.format('25'), shell = True)
	    subprocess.call(EXPORT_CMD.format('26'), shell = True)
	    subprocess.call(EXPORT_CMD.format('27'), shell = True)
	    subprocess.call(DIRECTION_CMD.format('25'),shell = True)
	    subprocess.call(DIRECTION_CMD.format('26'),shell = True)
	    subprocess.call(DIRECTION_CMD.format('27'),shell = True)
    
    adc = ADC(0)
    
    updateInterval = 5

    lastTime = 0
    lastBanner = 30
    isConnected = False

    try:
        with open("/etc/Scripts/mqtt_cred.json", "r") as configfile:
            mqttcred = json.load(configfile)
    except:
        mqttcred = {'broker':None, 'user':None, 'password': None}

    client = mqtt.Client(protocol=mqtt.MQTTv31)
    client.on_connect = on_connect
    client.on_message = on_message

    client.username_pw_set(mqttcred['user'], mqttcred['password'])
    client.connect(mqttcred['broker'], 1883, 60)
    
    client.loop_start()
    while isConnected == False:
        time.sleep(0.1)

    try:
        while True:
            now = time.time()
            if lastBanner > 20:
                lastBanner = 0
                # print("Vbus\tIbus\tVsupply\tVshunt\tPower")

            if now - lastTime > updateInterval:
                redOn()
                lastTime = now

                data['time'] = int(time.time())
                if physicalSensor.get_sensor_data() and physicalSensor.data.heat_stable:
                    data['GasResistance'] = physicalSensor.data.gas_resistance
                    data['HUM'] = physicalSensor.data.humidity
                    data['TEMPERATURE'] = physicalSensor.data.temperature
                    data['PRES'] = physicalSensor.data.pressure
                    data['OUTAQ'] = calculateScore(data['GasResistance'], data['HUM'])
                redOff()
                blueOn()

                data['IRRA'] = adc.value(3) * 0.9765625
                data['SND'] = (83.2072 + adc.value(2)) / 11.003
                if adc.value(1) > 800:
                    data['MOTION'] = 1
                else:
                    data['MOTION'] = 0
            
                blueOff()

                time.sleep(updateInterval)
                lastBanner += 1

                msg = json.dumps(data)
                client.publish(f"{mqttcred['topic']}", msg)
                print(f"Publishing to {mqttcred['broker']} topic {mqttcred['topic']}: {msg}")
    except KeyboardInterrupt:
        client.disconnect()
        client.loop_stop
