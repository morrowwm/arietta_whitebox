import time
import os
import gc
import subprocess

RED_PATH = """/sys/class/gpio/pioA25/value"""
GREEN_PATH = """/sys/class/gpio/pioA26/value"""
BLUE_PATH = """/sys/class/gpio/pioA27/value"""
EXPORT_CMD = 'echo {0} > /sys/class/gpio/export'
DIRECTION_CMD = 'echo out > /sys/class/gpio/pioA{0}/direction'

# Create paths if they don't exist already
if not os.path.exists(BLUE_PATH):
	print('Exporting paths')
	subprocess.call(EXPORT_CMD.format('25'), shell = True)
	subprocess.call(EXPORT_CMD.format('26'), shell = True)
	subprocess.call(EXPORT_CMD.format('27'), shell = True)
	subprocess.call(DIRECTION_CMD.format('25'),shell = True)
	subprocess.call(DIRECTION_CMD.format('26'),shell = True)
	subprocess.call(DIRECTION_CMD.format('27'),shell = True)


def test():
	print("Red")
	redOn()
	time.sleep(2)
	redOff()

	print('Blue')
	blueOn()
	time.sleep(2)
	blueOff()

	print('Green')
	greenOn()
	time.sleep(2)
	greenOff()


def blink():
	# only one blink happens at a time
	file = open(GREEN_PATH, 'r')
	check = file.read().strip()
	file.close()

	if check == '1':
		for x in range(10):
			greenOn()
			time.sleep(1)
			greenOff()
			time.sleep(1)

	del(check)
	gc.collect()
	os._exit(1)


def greenblink():
	while True:
		greenOn()
		time.sleep(1)
		greenOff()
		time.sleep(1)


def redoncheck():
	file = open(RED_PATH, 'r')
	red_check = file.read().strip()
	file.close()
	return red_check


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


# Turn off all lights on file import
greenOff()
redOff()


if os.path.isfile('/etc/bluelightcheck'):
	file = open("/etc/bluelightcheck","r")
	bluecheck = file.read().strip()
	file.close()
	if bluecheck == "False":
		blueOff()
else:
	blueOff()

def rgboff():
        greenOff()
        redOff()
        blueOff()

if __name__ == "__main__":
    test()
    rgboff()
