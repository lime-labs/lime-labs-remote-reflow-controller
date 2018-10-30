# just a quick script to log current temps from the thermocouple

import requests, time
from configparser import ConfigParser

# read in config file
parser = ConfigParser()
parser.read('settings.conf')

thermocouple_ip = parser.get('basics', 'thermocouple_ip')
unit = parser.get('basics', 'unit')

# set timestamp baseline for data gathering / graph plotting
time_base = time.time()


def getTemp():
    r = requests.get('http://' + thermocouple_ip + '/' + unit)
    temp = r.json()[unit]
    timestamp = round(time.time() - time_base, 2)
    # TODO: create graph ouput from gathered data after the run. Maybe just a CSV file for starters

    runtime = int(time.time() - time_base)
    minutes = int(runtime / 60)
    seconds = runtime % 60
    if seconds < 10:
        seconds = '0' + str(seconds)

    print('Time: ' + str(minutes) + ':' + str(seconds))
    print('>>>>>>>>>>>>>>>>> ' + str(temp))

    return temp


try:
    thermocouple_status = requests.get('http://' + thermocouple_ip + '/' + unit).status_code

    if thermocouple_status == 200:
        print('Succesfully connected to the thermocouple')
except:
    print('Error connecting to the thermocouple. Please check your settings and network status.')
    exit(1)


temp = getTemp()
previous_temp = temp

while True:
    temp = getTemp()
    kpersec = temp - previous_temp
    print('>>> K/s: ' + str(kpersec))
    previous_temp = temp
    time.sleep(1)