import asyncio
import time
import websockets
import smbus
import bme680
import json

BUS = smbus.SMBus(0)
eyeOrEnv = 0
envData = {}

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

async def getTemps():
    global eyeOrEnv
    dataString = ''
    record = []
    # breakpoint()
    try:
        if eyeOrEnv == 0:
            eyeOrEnv = 1
            record.append("eye")
            minv = [500, 0, 0]
            maxv = [-500 , 0, 0]
            for line in range(8):
                # lines = []
                offset = 0x80+line*16
                block = BUS.read_i2c_block_data(0x68,offset, 16)
                for j in range(0, 16, 2):
                    upper = block[j+1] << 8
                    lower = block[j]
                    val = upper + lower
                    if 2048 & val == 2048:
                        val -= 4096
                    val = round(0.2 * val, 2)
                    record.append(str(val))
            dataString = ','.join(record)
        elif eyeOrEnv == 1:
            eyeOrEnv = 0
            if physicalSensor.get_sensor_data() and physicalSensor.data.heat_stable:
                gas = round(physicalSensor.data.gas_resistance,2)
                hum = round(physicalSensor.data.humidity,2)
                temp = round(physicalSensor.data.temperature,2)
                pressure = round(physicalSensor.data.pressure,2)
                airScore=round(calculateScore(gas,hum),2)
                envData['type'] = 'env'
                envData['GasResistance'] = gas
                envData['MOBIHUMIDITY'] = hum
                envData['MOBITEMPERATURE'] = temp
                envData['MOBIBP'] = pressure
                envData['AirQuality'] = airScore
                dataString = json.dumps(envData)
                print(dataString)
    except:
        print('error reading')
    return(dataString)

async def recvMessage(websocket):
    message = websocket.recv()
    # print(f"Received {message}")
    return message

async def consumer(message):
    # print(f"Consumed {message}")
    nothing = True

# create receiver for each connection
async def handler(websocket, path):
    while True:
        listener_task = asyncio.ensure_future(recvMessage(websocket))
        producer_task = asyncio.ensure_future(getTemps())
        done, pending = await asyncio.wait(
            [listener_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED)

        if listener_task in done:
            message = listener_task.result()
            await consumer(message)
        else:
            listener_task.cancel()

        if producer_task in done:
            message = producer_task.result()
            await websocket.send(message)
        else:
            producer_task.cancel()

start_server = websockets.serve(handler, host=None, port=8000)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
