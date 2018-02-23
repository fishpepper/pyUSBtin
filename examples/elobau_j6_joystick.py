#################################################
# configuration:
#################################################
# serial port
port = "/dev/ttyACM0"

# id of joystick (fixed, no need to change this)
j6_can_id = 0x10
#################################################

# install pyusbtin: 
from pyusbtin.usbtin import USBtin
from pyusbtin.canmessage import CANMessage
# install python-evdev
from evdev import UInput, ecodes, AbsInfo
# misc
from time import sleep
import atexit

class vjoy(object):
    """ send virtual joystick data to linux event system   """
    def __init__(self, can_id):
        self.can_id = can_id
        axis_cap = AbsInfo(-32700,32700,0,0,0,0)
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
        #print(msg)
        if (msg.mid == (0x180+self.can_id)):
            # convert axis data to signed
            abs_x = (msg[0] - 256) if (msg[0]>127) else msg[0]
            abs_y = (msg[1] - 256) if (msg[1]>127) else msg[1]
            abs_z = (msg[2] - 256) if (msg[2]>127) else msg[2]
            # flip y
            abs_y = -abs_y
            # rescale from -100..100 to -32700..32700:
            abs_x = abs_x * 327
            abs_y = abs_y * 327
            abs_z = abs_z * 327
            # fetch buttons
            b0 = 1 if (msg[5] & 32) else 0
            b1 = 1 if (msg[5] & 1) else 0
            b2 = 1 if (msg[5] & 8) else 0
            # debug data
            print(" X: " + str(abs_x) + " Y: " + str(abs_y) + " Z: " + str(abs_z) + " B0: " + str(b0) + " B1: " + str(b1) + " B2: " + str(b2))
            # send data
            self.signal(abs_x, abs_y, abs_z, b0, b1, b2)


class canopen_joystick(object):
    """ joystick via usbtin canopen """
    def __init__(self, port, can_id):
        self.can_id = can_id

        # create virtual joystick output device
        self.joy = vjoy(can_id)

        # open can interface
        self.usbtin = USBtin()
        self.usbtin.connect(port)

        # create data listener
        self.usbtin.add_message_listener(self.joy.process_can_data)

        # open can bus at 250kbaud
        self.usbtin.open_can_channel(250000, USBtin.ACTIVE)

        # set defaults
        self.set_active(1)
        self.set_led(1)

        # register on exit handler
        atexit.register(self.__exit__, self, 0, 0)

    def set_active(self, state):
        # start/stop canopen data transfer
        if (state):
            data = [0x01, self.can_id]
        else: 
            data = [0x00, self.can_id]
        # send can message
        self.usbtin.send(CANMessage(0x000, data))

    def set_led(self, state):
        # switch on/off all leds
        if (state):
            data = "\x55\x55\x55\x55\x55\x55\x55\x55"
        else:
            data = "\x00\x00\x00\x00\x00\x00\x00\x00"
        # send PDO
        self.usbtin.send(CANMessage(0x200+self.can_id, data))

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.set_led(0)
        self.set_active(0)
        self.usbtin.disconnect()

# intantiate joystick object. data transfer is done inside the usbtin thread
j6 = canopen_joystick(port, j6_can_id)

while(True):
    sleep(0.5)
