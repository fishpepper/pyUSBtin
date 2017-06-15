from __future__ import absolute_import, division, print_function

from pyusbtin.usbtin import USBtin
from pyusbtin.canmessage import CANMessage
from time import sleep
from pprint import pprint

CANMessage.load_dbc(r'example.dbc')
pprint(CANMessage.dbc_info)

print('\n'*2)

engine = CANMessage(0x100)
print(engine)

engine.RPM = 2000
engine.Torque = 125

print(engine)

brake = CANMessage(0x200)
brake[2] = 0x15
print(brake)

unknown_with_data = CANMessage(0x1, [0xAA, 0xBB, 0xCC])
print(unknown_with_data)


def log_data(msg):
    print('received {}'.format(hex(msg.mid)))
    print(msg)

print('\n'*2)

usbtin = USBtin()
usbtin.connect("COM11")
usbtin.add_message_listener(log_data)
usbtin.open_can_channel(500000, USBtin.LOOPBACK)

usbtin.send(engine)
sleep(0.1)
usbtin.send(brake)
sleep(0.1)
usbtin.send(unknown_with_data)
sleep(0.1)

