# Lime Labs GmbH
# https://limelabs.io
#
# lime labs remote reflow controller
#
# A simple, Python 3 based remote toaster/hot-plate/reflow oven controller.
# Works over the network with smart power plugs (like TP-Link's HS100/110) and remote thermocouples
# (like our "lime labs wifi thermocouple", see https://github.com/lime-labs/lime-labs-wifi-thermocouple).
# No need to ever touch or fiddle with mains power!
#
# @author: Peter Winter <code@limelabs.io>
# @version: 1.0.0
# @date: 10/29/2018

import requests, time
import tplink_smartplug as plug
# TCP only thermocouple readout is WIP
#import thermocouple_tcp as tc
from configparser import ConfigParser

# set timestamp baseline for data gathering / graph plotting
time_base = time.time()

# read in config files
parser = ConfigParser()
parser.read('settings.conf')

# frequency = float(parser.get('basics', 'frequency'))
plug_ip = parser.get('basics', 'plug_ip')
thermocouple_ip = parser.get('basics', 'thermocouple_ip')
unit = parser.get('basics', 'unit')
profile_file = parser.get('basics', 'profile')

# now the parser refers to the reflow profile file
parser.read(profile_file)
unit_profile = parser.get('basics', 'temp_unit')

# preflight checks
if unit != unit_profile:
    print('ERROR: settings unit entry doesn\'t match the reflow profile temperature unit!')
    exit(1)

print('Using reflow profile \"' + parser.get('basics', 'name') + '\", with temperature unit ' + unit_profile)

try:
    thermocouple_status = requests.get('http://' + thermocouple_ip + '/' + unit).status_code
    plug_status = plug.sendCommand(plug_ip, 'info')['system']['get_sysinfo']

    if thermocouple_status == 200 and plug_status['err_code'] == 0:
        print('Succesfully connected to the thermocouple and the smart plug with alias ' + plug_status['alias'] + ', model ' + plug_status['model'])
except:
    print('Error connecting to the thermocouple or smart plug. Please check your settings and network status.')
    exit(1)

# functions
def getTemp():
    r = requests.get('http://' + thermocouple_ip + '/' + unit)
    temp = r.json()[unit]
    timestamp = round(time.time() - time_base, 2)
    # TODO: create graph ouput from gathered data after the run. Maybe just a CSV file for starters
    print(temp)
    print(str(timestamp))
    return temp

def getPlugRelayState():
    relay_state = plug.sendCommand(plug_ip, 'info')['system']['get_sysinfo']['relay_state']
    if relay_state == 0:
        return 'off'
    elif relay_state == 1:
        return 'on'
    else:
        return 'error'

def rampUp(phase, maxKpersec, target, duration = -1, reflow_temp = 0.0, peak_start = 0.0, duration_at_peak = -1):
    temp = getTemp()
    previous_temp = temp
    plug_status = getPlugRelayState()

    print('Entering ' + phase + ' phase. Settings: ' + str(maxKpersec) + ' K/s, target temp ' +  str(target))

    # temporarily save the value to reset to it during reflow phase
    reset_reflow_duration_to = duration
    reflow_reset = False
    peak_reset = False

    while temp <= target and duration != 0:
        temp = getTemp()
        kpersec = temp - previous_temp

        # only used during reflow phase to remain at least duration seconds within the reflow region
        if phase == 'reflow' and 0.0 < reflow_temp <= temp:
            if not reflow_reset:
                duration = reset_reflow_duration_to
                reflow_reset = True
            print('Reflow temp of ' + str(reflow_temp) + ' degrees reached). ' + str(duration) + ' seconds remaining in reflow zone.')

        # limiting the duration in the peak zone if reached
        if phase == 'reflow' and peak_start != 0.0 and temp >= peak_start:
            if duration > duration_at_peak:
                if not peak_reset:
                    duration = duration_at_peak
                    peak_reset = True
            print('Peak zone of ' + str(peak_start) + ' - ' + target + ' degrees reached). ' + str(duration) + ' seconds remaining in peak zone.')

        if kpersec > maxKpersec:
            print('Max K/s reached, waiting before continuing to ramp up...')
            if plug_status == 'on':
                plug.sendCommand(plug_ip, 'off')
                plug_status = 'off'
        else:
            if plug_status == 'off':
                plug.sendCommand(plug_ip, 'on')
                plug_status = 'on'

        print('K/s ' + str(kpersec))
        previous_temp = temp
        duration -= 1
        time.sleep(1)

    # in case there's time left on the optional duration timer, hold the temp for the remainder of seconds
    if duration > 0:
        print('Target temp of ' + str(target) + ' reached, but ' + duration + ' seconds left on timer. Holding temp...')
        while duration > 0:
            temp = getTemp()

            # give it a 1 % buffer to drop below or rise above the target temp before triggering the smart plug again
            if (temp + (target / 100)) < target and plug_status == 'off':
                plug.sendCommand(plug_ip, 'on')
                plug_status = 'on'

            if (temp - (target / 100)) > target and plug_status == 'on':
                plug.sendCommand(plug_ip, 'off')
                plug_status = 'off'

            duration -= 1
            time.sleep(1)

    print('finished ' + phase + ' phase, entering next phase...')


def coolDown(maxKpersec, target):
    print('Reflow done. Beginning cooldown phase...')
    plug.sendCommand(plug_ip, 'off')
    # TODO: play sound here
    print('Toaster/hot-plate/oven has been switched off. Open the door or slowly remove PCB from heating source to let it cool down gracefully.')

    temp = getTemp()
    previous_temp = temp

    while temp > target:
        temp = getTemp()
        kpersec = temp - previous_temp

        # if cooldown happens to fast
        if kpersec < maxKpersec:
            print('>>>>>> WARNING! Cooldown rate exceeds ' + maxKpersec + ' K/s at currently ' + kpersec + ' K/s.')
            print('>>>>>> Consider less aggressive cooling to reduce stress on the components!')
        else:
            print('K/s ' + str(kpersec))

        previous_temp = temp
        time.sleep(1)

    # TODO: play sound here
    print('Congrats! Your PCB is ready. Be careful, it might still be a little warm at ' + target + ' degrees.')


# let's roll

# preheating
target = float(parser.get('preheating', 'target'))
maxkpersec = int(parser.get('preheating', 'maxkpersec'))

rampUp('preheating', maxkpersec, target)

# soak
target = float(parser.get('soak', 'end'))
duration = int(parser.get('soak', 'duration'))
maxkpersec = (float(parser.get('soak', 'end')) - float(parser.get('soak', 'start'))) / int(parser.get('soak', 'duration'))

rampUp('soak', maxkpersec, target, duration)

# reflow
reflow_temp = float(parser.get('reflow', 'reflow_temp'))
duration = int(parser.get('reflow', 'duration'))
target = float(parser.get('reflow', 'max_temp'))
peak_start = float(parser.get('reflow', 'peak_start'))
duration_at_peak = int(parser.get('reflow', 'duration_at_peak'))
maxkpersec = int(parser.get('reflow', 'maxkpersec'))

rampUp('reflow', maxkpersec, target, duration, reflow_temp, peak_start, duration_at_peak)

# cooldown
target = float(parser.get('cooldown', 'target'))
maxkpersec = int(parser.get('cooldown', 'maxkpersec'))

coolDown(maxkpersec, target)

runtime = int(time.time() - time_base)
minutes = int(runtime / 60)
seconds = runtime % 60
print('The entire reflow process took ' + str(minutes) + ':' + str(seconds) + ' minutes.')

exit(0)
