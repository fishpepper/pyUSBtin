from pyusbtin.usbtin import USBtin
from pyusbtin.canmessage import CANMessage
from time import sleep

def log_data(msg):
    print(msg)

usbtin = USBtin()
usbtin.connect("/dev/ttyACM0")
usbtin.add_message_listener(log_data)
usbtin.open_can_channel(100000, USBtin.ACTIVE)

#send an "ignition is on" message in order to wake
#up other can devices 
ignition_msg = CANMessage(0x575, "\x0B\x10\x00\x00")

while(True):
    usbtin.send(ignition_msg)
    sleep(0.1)
