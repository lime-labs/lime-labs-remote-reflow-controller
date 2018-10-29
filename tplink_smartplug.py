# TP-Link Wi-Fi Smart Plug Protocol Client
# For use with TP-Link HS-100 or HS-110
#
# modified (reduced and converted to Python 3) in 2018 for use in our remote toaster/hot-plate/reflow oven controller project
# (https://github.com/lime-labs/lime-labs-remote-reflow-controller)
# by Peter Winter, Lime Labs GmbH <code@limelabs.io>
#
# original code from https://github.com/softScheck/tplink-smartplug
# by Lubomir Stroetmann
# Copyright 2016 softScheck GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket, json
from struct import pack

port = 9999

# Predefined Smart Plug Commands
# For a full list of commands, consult tplink_commands.txt
commands = {'info'     : '{"system":{"get_sysinfo":{}}}',
            'on'       : '{"system":{"set_relay_state":{"state":1}}}',
            'off'      : '{"system":{"set_relay_state":{"state":0}}}',
            'cloudinfo': '{"cnCloud":{"get_info":{}}}',
            'wlanscan' : '{"netif":{"get_scaninfo":{"refresh":0}}}',
            'time'     : '{"time":{"get_time":{}}}',
            'schedule' : '{"schedule":{"get_rules":{}}}',
            'countdown': '{"count_down":{"get_rules":{}}}',
            'antitheft': '{"anti_theft":{"get_rules":{}}}',
            'reboot'   : '{"system":{"reboot":{"delay":1}}}',
            'reset'    : '{"system":{"reset":{"delay":1}}}',
            'energy'   : '{"emeter":{"get_realtime":{}}}'
}

# Encryption and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171
def encrypt(string):
    key = 171
    result = bytearray(pack('>I', len(string)))
    for i in string:
        a = key ^ ord(i)
        key = a
        result.append(a)
    return result

def decrypt(bytes):
    key = 171
    result = ""
    for i in bytes:
        a = key ^ i
        key = i
        result += chr(a)
    return result

def sendCommand(ip, command):
    cmd = commands[command]

    try:
        sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_tcp.connect((ip, port))
        sock_tcp.send(encrypt(cmd))
        data = sock_tcp.recv(2048)
        sock_tcp.close()

        result = decrypt(data[4:])
        return json.loads(result)

    except socket.error:
        print("Could not connect to smart plug at " + ip + ":" + str(port))
