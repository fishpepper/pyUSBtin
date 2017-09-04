"""
This file is part of pyusbtin

Copyright(c) 2016 fishpepper <AT> gmail.com
http://github.com/fishpepper/pyusbtin

This file may be licensed under the terms of the
GNU General Public License Version 3 (the ``GPL''),
or (at your option) any later version.

Software distributed under the License is distributed
on an ``AS IS'' basis, WITHOUT WARRANTY OF ANY KIND, either
express or implied. See the GPL for the specific language
governing rights and limitations.

You should have received a copy of the GPL along with this
program. If not, go to http://www.gnu.org/licenses/gpl.html
or write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# imports
from __future__ import absolute_import, division, print_function
import serial
import sys
from time import sleep
#from thread import start_new_thread
import threading
from .usbtinexception import USBtinException
from .canmessage import CANMessage


PY_VERSION = sys.version_info[0]


# this class represents a can message
class USBtin(object):
    """ modes for opening a can channel:
     active
     Listen only, sending messages is not possible
     Loop back the sent CAN messages. Disconnected from physical CAN bus
    """
    ACTIVE, LISTENONLY, LOOPBACK = range(3)

    """ enums for rx thread """
    RX_THREAD_STOPPED, RX_THREAD_RUNNING, RX_THREAD_TERMINATE = range(3)

    """ timeout for readng from serial port """
    READ_TIMEOUT = 1000

    def __init__(self):
        """ initialiser """
        self.id = 0
        self.serial_number = 0
        self.firmware_version = 0
        self.hardware_version = 0

        self.serial_port = None

        self.rx_thread_state = USBtin.RX_THREAD_STOPPED

        self.incoming_message = ""

        self.listeners = []
        self.tx_fifo = []

    def get_firmware_version(self):
        """ get firmware version that was acquired during connect() """
        return self.firmware_version

    def get_hardware_version(self):
        """ get hardware version that was acquired during connect() """
        return self.hardware_version

    def get_serial_number(self):
        """ get serial number that was acquired during connect()"""
        return self.serial_number

    def connect(self, port):
        """Connect to USBtin on given port.
           Opens the serial port, clears pending characters and send close command
           to make sure that we are in configuration mode.

           Keyword arguments:
            port -- name of serial port

           Throws:
            USBtinException in case something goes wrong
        """
        try:
            # open serial port
            self.serial_port = serial.Serial(port, 115200, timeout=USBtin.READ_TIMEOUT, parity=serial.PARITY_NONE)

            # clear port and  make sure we are in configuration mode (close cmd)
            self.serial_port.write("\rC\r".encode('ascii'))
            sleep(0.1)

            self.serial_port.flush()
            self.serial_port.flushInput()  # reset_input_buffer()

            print("sending clear port request")
            self.serial_port.write("C\r".encode('ascii'))

            while True:
                b = self.serial_port.read(1)
                #print("RX 0x%02X" % b)
                if b in (b'\r', b'\x07'):
                    break

            # clear port and get version strings
            self.firmware_version = self.transmit("v")[1:]
            self.hardware_version = self.transmit("V")[1:]
            self.serial_number = self.transmit("N")[1:]

            # some debug info
            print("connected to USBtin fw %s, hw %s (serial %s)" % (self.firmware_version, self.hardware_version, self.serial_number))

            # reset overflow error flags
            self.transmit("W2D00")

        except serial.SerialException as e:
            raise USBtinException("{0} - {1}: {2}".format(port, e.errno, e.strerror))

    def transmit(self, cmd):
        """Transmit given command to USBtin

           Keyword arguments:
            cmd -- Command
        """
        print("sending [" + cmd + "]")
        self.serial_port.write((cmd + "\r").encode('ascii'))
        if self.rx_thread_state != USBtin.RX_THREAD_RUNNING:
            return self.read_response()

    def read_response(self):
        """ Read response from USBtin"""
        if self.rx_thread_state != USBtin.RX_THREAD_STOPPED:
            raise USBtinException("ERROR: you can not call rx on the serial" +
                                  "port when the main rx thread is running!")

        response = b''
        while True:
            b = self.serial_port.read(1)
            if b == b'\r':
                break
            elif b == b'\x07':
                raise USBtinException(self.serial_port.name, "transmit", "BELL signal")
            else:
                response += b
        return response

    def disconnect(self):
        """Disconnect. Close serial port connection"""
        try:
            self.stop_rx_thread()
            self.serial_port.close()
        except serial.SerialException as e:
            raise USBtinException("{0} - {1}: {2}".format(self.serial_port.name, e.errno, e.strerror))

    def open_can_channel(self, baudrate, mode):
        """Open CAN channel.
           Set given baudrate and open the CAN channel in given mode.

           Keyword arguments:
            baudrate -- Baudrate in bits/second
            mode -- CAN bus accessing mode
        """
        try:
            baud_dict = {
                10000: '0',
                20000: '1',
                50000: '2',
                100000: '3',
                125000: '4',
                250000: '5',
                500000: '6',
                800000: '7',
                1000000: '8'
            }

            if baudrate in baud_dict:
                # use preset baudrate
                self.transmit("S" + baud_dict[baudrate])
            else:
                # calculate baudrate register settings
                fosc = 24000000.0
                xdesired = fosc / baudrate
                xopt = 0
                diffopt = 0
                brpopt = 0

                # walk through possible can bit length (in TQ)
                for x in range(11, 23 + 1):
                    # get next even value for baudrate factor
                    xbrp = (xdesired * 10) / x
                    m = xbrp % 20
                    if m >= 10:
                        xbrp += 20
                    xbrp -= m
                    xbrp /= 10

                    # check bounds
                    if xbrp < 2:
                        xbrp = 2

                    if xbrp > 128:
                        xbrp = 128

                    # calculate diff
                    xist = x * xbrp
                    diff = xdesired - xist
                    if diff < 0:
                        diff = -diff

                    # use this clock option if it is better than previous
                    if (xopt == 0) or (diff <= diffopt):
                        xopt = x
                        diffopt = diff
                        brpopt = xbrp / 2 - 1
                # mapping for CNF register values
                cnfvalues = [0x9203, 0x9303, 0x9B03, 0x9B04, 0x9C04, 0xA404, 0xA405, 0xAC05, 0xAC06, 0xAD06, 0xB506,
                             0xB507, 0xBD07]

                # build command
                cmd = "s{:02x}{:04x}".format(brpopt | 0xC0, cnfvalues[xopt - 11])
                self.transmit(cmd)
                print("no preset for given baudrate %d. Set baudrate to %d" %
                      (baudrate, (fosc / ((brpopt + 1) * 2) / xopt)))

            # open can channel
            mode_dict = {USBtin.LISTENONLY: 'L', USBtin.LOOPBACK: 'l', USBtin.ACTIVE: 'O'}
            mode_tx = 'L'

            if mode in mode_dict:
                mode_tx = mode_dict[mode]
            else:
                print("Mode %d not supported. Opening listen only." % mode)

            self.transmit(mode_tx)

            # start rx thread:
            self.start_rx_thread()

        except serial.SerialTimeoutException as e:
            raise USBtinException(e)

    def start_rx_thread(self):
        """ start the serial receive thread"""
        self.rx_thread_state = USBtin.RX_THREAD_RUNNING
        thread = threading.Thread(target=self.rx_thread, args=())
        thread.daemon = True
        thread.start()
        #start_new_thread(self.rx_thread, (self, self.serial_port))

    def stop_rx_thread(self):
        """ stop the serial receive thread.
            note: this will block until the thread was shut down"""
        if self.rx_thread_state == USBtin.RX_THREAD_STOPPED:
            # already stopped, thus return
            return

        # tell the thread to exit
        self.rx_thread_state = USBtin.RX_THREAD_TERMINATE
        while self.rx_thread_state != USBtin.RX_THREAD_STOPPED:
            # wait for thread to end, sleep 1ms
            sleep(0.001)

    def rx_thread(self):
        """ main rx thread. this thread will take care to
            handle the data from the serial port"""
        print("rx thread started")

        """ process data as long as requested """
        while self.rx_thread_state == USBtin.RX_THREAD_RUNNING:
            # fetch bytes if available
            rxcount = self.serial_port.inWaiting()
            if rxcount > 0:
                # fetch all data from serial buffer
                buf = self.serial_port.read(rxcount)
                if PY_VERSION == 2:
                    buf = [ord(b) for b in buf]

                for b in buf:
                    if (b == ord('\r')) and len(self.incoming_message) > 0:
                        message = self.incoming_message
                        cmd = message[0]
                        if cmd in 'tTrR':
                            # create CAN message from message string
                            canmsg = CANMessage.from_string(message)

                            # give the CAN message to the listeners
                            for listener in self.listeners:
                                listener(canmsg)
                        elif cmd in 'zZ':
                            # remove first message from transmit fifo and send next one
                            self.tx_fifo.pop(0)

                            try:
                                self.send_first_tx_fifo_message()
                            except USBtinException as e:
                                print(e)

                        # clear message
                        self.incoming_message = ""

                    elif b == 0x07:
                        # resend first element from tx fifo
                        try:
                            self.send_first_tx_fifo_message()
                        except USBtinException as e:
                            print(e)

                    elif b != ord('\r'):
                        self.incoming_message += chr(b)
        # thread stopped...
        self.rx_thread_state = USBtin.RX_THREAD_STOPPED

    def close_can_channel(self):
        """Close CAN channel."""
        try:
            self.stop_rx_thread()
            self.serial_port.write("C\r".encode('ascii'))
        except serial.SerialTimeoutException as e:
            raise USBtinException(e)

        self.firmware_version = 0
        self.hardware_version = 0

    def add_message_listener(self, func):
        """ add a message listener (callback)"""
        self.listeners.append(func)

    def remove_message_listener(self, func):
        """ remove message listemer"""
        if func in self.listeners:
            self.listeners.remove(func)
        else:
            raise USBtinException("ERROR: failed to remove listener")

    def send_first_tx_fifo_message(self):
        """ Send first message in tx fifo """
        if len(self.tx_fifo) == 0:
            return

        canmsg = self.tx_fifo[0]

        try:
            self.serial_port.write('{}\r'.format(canmsg.to_string()).encode('ascii'))
        except serial.SerialTimeoutException as e:
            raise USBtinException(e)

    def send(self, canmsg):
        """ Send given can message. """
        self.tx_fifo.append(canmsg)

        if len(self.tx_fifo) > 1:
            return
        else:
            self.send_first_tx_fifo_message()

    def write_mcp_register(self, register, value):
        """Write given register of MCP2515

        Keyword arguments:
         register -- Register address
         value -- Value to write
        """
        try:
            cmd = "W{:02x}{:02x}".format(register, value)
            self.transmit(cmd)
        except serial.SerialTimeoutException as e:
            raise USBtinException(e)

    def write_mcp_filter_mask_registers(self, maskid, registers):
        """ Write given mask registers to MCP2515

            Keyword arguments:
            maskid -- Mask identifier (0 = RXM0, 1 = RXM1)
            registers -- Register values to write
        """
        for i in range(4):
            self.write_mcp_register(0x20 + maskid * 4 + i, registers[i])

    def write_mcp_filter_registers(self, filterid, registers):
        """Write given filter registers to MCP2515

           Keyword arguments:
           filterid -- Filter identifier (0 = RXF0, ... 5 = RXF5)
           registers -- Register values to write
         """
        startregister = [0x00, 0x04, 0x08, 0x10, 0x14, 0x18]
        for i in range(4):
            self.write_mcp_register(startregister[filterid] + i, registers[i])

    def set_filter(self, fc):
        """ Set hardware filters.
            Call this function after connect() and before openCANChannel()!

            Keyword arguments:
            fc -- Filter chains (USBtin supports maximum 2 hardware filter chains)

            NOTE:
             The MCP2515 offers two filter chains. Each chain consists
             of one mask and a set of filters:

              RXM0         RXM1
                |            |
              RXF0         RXF2
              RXF1         RXF3
                           RXF4
                           RXF5
        """
        # if no filter chain given, accept all messages
        if not fc:
            registers = [0x00, 0x00, 0x00, 0x00]
            self.write_mcp_filter_mask_registers(0, registers)
            self.write_mcp_filter_mask_registers(1, registers)
            return

        # check maximum filter channels
        if len(fc) > 2:
            raise USBtinException("Too manx filter chains %d (maximum is 2)!" % len(fc))

        # swap channels if necessary and check filter chain length
        if len(fc) == 2:
            if len(fc[0].get_filters()) > len(fc[1].get_filters()):
                # swap [0]<-->[1]
                fc[0], fc[1] = fc[1], fc[0]

            if (len(fc[0].get_filters()) > 2) and (len(fc[1].get_filters()) > 4):
                raise USBtinException("Filter chain too long: %d / %d (max is 2/4)!" %
                                      (len(fc[0].get_filters()), len(fc[1].get_filters())))
        elif len(fc) == 1:
            if len(fc[0].get_filters()) > 4:
                raise USBtinException("Filter chain too long: %d (maximum is 4)!" % len(fc[0].get_filters()))

        # set MCP2515 filter/mask registers; walk through filter channels
        filterid = 0
        fcidx = 0

        for channel in range(2):
            # set mask
            self.write_mcp_filter_mask_registers(channel, fc[fcidx].get_mask().get_registers())

            # set filters
            registers = [0x00, 0x00, 0x00, 0x00]
            for i in range(2 * (1 + channel)):
                if len(fc[fcidx].get_filters()) > i:
                    registers = fc[fcidx].get_filters()[i].get_registers()

                self.write_mcp_filter_registers(filterid, registers)
                filterid += 1

                # go to next filter chain if available
                if len(fc) - 1 > fcidx:
                    fcidx += 1
