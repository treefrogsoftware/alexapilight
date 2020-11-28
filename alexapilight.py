import logging
import os
import json

from flask import Flask
from flask_ask import Ask, request, session, question, statement
import subprocess


app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)

STATUSON = ['on','high']
STATUSOFF = ['off','low']
BASE_COMMAND = "/usr/local/bin/pilight-send -p %s "
UNIT_COMMAND = "%s %d -u %d %s "
NAME_COMMAND = "-n %s "
PROGRAM_COMMAND = "%s %d -u %d "
SERVER_COMMAND = "%s -S=127.0.0.1 -P=5000"

PILIGHT_CONFIG = "/etc/pilight/config.json"

SEND_ON="-t"
SEND_OFF="-f"
SYS_CODE="-s"
ID_CODE="-i"

device_list = []
class Device:
    def __init__(self, name, protocol, id, unit, systemcode):
        self.name = name
        self.protocol = protocol
        self.id = id
        self.unit = unit
        self.systemcode = systemcode

def loadDevices():
    with open(PILIGHT_CONFIG) as json_file:
        data = json.load(json_file)

    node = data['devices']
    for key, value in node.items():
        unit_node = value['id'][0]
        protocol = value['protocol'][0]
        systemcode = False
        if 'id' in unit_node:
            id = unit_node['id']
            unit = unit_node['unit']
        elif protocol is 'program':
            id = unit_node['name']
            unit = 0
            systemcode = False
        else:
            id = unit_node['systemcode']
            unit = unit_node['unitcode']
            systemcode = True

        device_list.append(Device(key, protocol, id, unit, systemcode))

def getDevice(name):
    return next((device for device in device_list if device.name.lower() == name.lower()), None)

#loadDevices()

@ask.launch
def launch():
    speech_text = 'Welcome to Raspberry Pi Automation. Supported devices are: '.join(device_list)
    return question(speech_text).reprompt(speech_text).simple_card(speech_text)


@ask.intent('pilight', mapping = {'status':'status','deviceName':'device'})
def pilight(status,deviceName):
    print(deviceName, status)
    device = getDevice(deviceName)

    if device is not None:
        switch(device, status)
        return statement('turning {} {} lights'.format(status, device.name))
    else:
        return statement('Sorry not possible.')


@ask.intent('AMAZON.HelpIntent')
def help():
    speech_text = 'You can say hello to me!'
    return question(speech_text).reprompt(speech_text).simple_card('HelloWorld', speech_text)


def switch(device, status):
    system_flag = SYS_CODE if device.systemcode else ID_CODE
    on_flag = SEND_ON if status in STATUSON else SEND_OFF

    if device.protocol is not 'program':
        command = COMMAND % (device.protocol) + UNIT_COMMAND % (system_flag, device.id, device.unit) + BASE_COMMAND % (on_flag)
    else:
        command = COMMAND % (device.protocol) + NAME_COMMAND % (device.id) + BASE_COMMAND % on_flag

    print(command)
    returned_value = subprocess.call(command, shell=True)  # returns the exit code in unix
    print('returned value:', returned_value)
    return True


@ask.session_ended
def session_ended():
    return "{}", 200


if __name__ == '__main__':
    if 'ASK_VERIFY_REQUESTS' in os.environ:
        verify = str(os.environ.get('ASK_VERIFY_REQUESTS', '')).lower()
        if verify == 'false':
            app.config['ASK_VERIFY_REQUESTS'] = False
    loadDevices()
    app.run(host='0.0.0.0', port=5003, debug=True)


