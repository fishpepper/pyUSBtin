# install pyusbtin: 
from pyusbtin.usbtin import USBtin
from pyusbtin.canmessage import CANMessage
# install python-evdev
from evdev import UInput, ecodes, AbsInfo
# misc
from time import sleep

class vjoy(object):
    """ send virtual joystick data to linux event system   """
    def __init__(self):
        axis_cap = AbsInfo(0,20000,0,0,0,0)
        self._ev = UInput(name='vjoy',
            events={
                 ecodes.EV_ABS: [
                     (ecodes.ABS_X, axis_cap),
                     (ecodes.ABS_Y, axis_cap),
                     (ecodes.ABS_Z, axis_cap)
                 ],
                 ecodes.EV_KEY: [
                     ecodes.BTN_TRIGGER, 
                     ecodes.BTN_TOP, 
                     ecodes.BTN_TOP2
                 ]
            }
        )

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self._ev.close()

    def signal(self, x, y, z, b0, b1, b2):
       self._ev.write(ecodes.EV_ABS, ecodes.ABS_X, x)
       self._ev.write(ecodes.EV_ABS, ecodes.ABS_Y, y)
       self._ev.write(ecodes.EV_ABS, ecodes.ABS_Z, z)
       self._ev.write(ecodes.EV_KEY, ecodes.BTN_TRIGGER, b0)
       self._ev.write(ecodes.EV_KEY, ecodes.BTN_TOP,     b1)
       self._ev.write(ecodes.EV_KEY, ecodes.BTN_TOP2,    b2)
       self._ev.syn()	

    def process_can_data(self, msg):
        if (msg.mid == 0x190):
            #print(msg)
            # convert axis data to signed
            abs_x = (msg[0] - 256) if (msg[0]>127) else msg[0]
            abs_y = (msg[1] - 256) if (msg[1]>127) else msg[1]
            abs_z = (msg[2] - 256) if (msg[2]>127) else msg[2]
            # flip y
            abs_y = -abs_y
            # rescale from -100..100 to 0..20000:
            abs_x = ((abs_x+100) * 100)
            abs_y = ((abs_y+100) * 100)
            abs_z = ((abs_z+100) * 100)
            # fetch buttons
            b0 = 1 if (msg[5] & 32) else 0
            b1 = 1 if (msg[5] & 1) else 0
            b2 = 1 if (msg[5] & 8) else 0
            # debug data
            print(" X: " + str(abs_x) + " Y: " + str(abs_y) + " Z: " + str(abs_z) + " B0: " + str(b0) + " B1: " + str(b1) + " B2: " + str(b2))
            # send data
            self.signal(abs_x, abs_y, abs_z, b0, b1, b2)
        
# create virtual joystick
joy = vjoy()

# open can interface
usbtin = USBtin()
usbtin.connect("/dev/ttyACM0")

# create data listener
usbtin.add_message_listener(joy.process_can_data)

usbtin.open_can_channel(250000, USBtin.ACTIVE)

# start data transfer
start_msg = CANMessage(0x000, "\x01\x10")
usbtin.send(start_msg)

while(True):
    sleep(0.1)
