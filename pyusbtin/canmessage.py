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

from __future__ import absolute_import, division, print_function
import sys

import re
from struct import pack, unpack

from .usbtinexception import USBtinException


PY_VERSION = sys.version_info[0]


# this class represents a can message
class CANMessage(object):
    """CAN message implementation.


    Examples
    --------
    >>> msg = CANMessage(0x100, [1, 2, 3, 4])
    >>> msg
    CAN message { id = 0x100  len = 4 [ 01 02 03 04 ]}
    >>> msg = CANMessage(0x200, (10, 20, 30))
    >>> msg
    CAN message { id = 0x200  len = 3 [ 0a 14 1e ]}
    >>> msg = CANMessage(0x50, b'example')
    >>> msg
    CAN message { id = 0x50  len = 7 [ 65 78 61 6d 70 6c 65 ]}
    >>> msg = CANMessage(0x300, dlc=6)
    >>> msg
    CAN message { id = 0x300  len = 6 [ 00 00 00 00 00 00 ]}
    >>> msg[3] = 0xFF
    CAN message { id = 0x300  len = 6 [ 00 00 00 ff 00 00 ]}
    >>> CANMessage.load_dbc('example.dbc')
    >>> msg = CANMessage(0x300)
    >>> msg
    CAN message { id = 0x300  len = 6 [ 00 00 00 00 00 00 ]}
    	                             RPM 0
    	                          Torque 0
    >>> msg.RPM = 6000
    >>> msg.Torque = 120
    >>> msg
    CAN message { id = 0x300  len = 6 [ 70 17 00 00 78 00 ]}
	                          Torque 120
	                             RPM 6000

    Attributes
    ----------
    mid : int
        message id
    name : str
        message name
    rtr : bool
        remote frame
    extended : bool
        extended message id
    dlc : int
        data length code
    dbc_info : dict
        static class attribute; contains messages description loaded from supplied DBC

    Parameters
    ----------
    mid : int
        message id
    data : sequence
        can be a list, tuple or bytes; default None
    rtr : bool
        remote frame flag; default False
    name : str
        message name; default ''
    dlc : int
        message DLC; default None
    """

    dbc_info = {}

    def __init__(self, mid, data=None, rtr=False, name='', dlc=None):

        if mid > 0x1fffffff:
            mid = 0x1fffffff

        self.mid = mid
        self.name = name
        self.rtr = rtr
        self.extended = True if mid > 0x7ff else False

        if rtr:
            if self.mid in self.dbc_info and dlc != self.dbc_info[self.mid]['dlc']:
                raise USBtinException('CAN ID {} data length missmatch: dbc says {} but {} was supplied in RTR'.format(hex(self.mid), self.dbc_info[self.mid]['dlc']), len(data))
            else:
                self.dlc = dlc
                self._data = 0
        else:
            if not data is None:
                # check if data length is equal to signal dlc as specified in dbc
                if self.mid in self.dbc_info:
                    if len(data) != self.dbc_info[self.mid]['dlc']:
                        raise USBtinException('CAN ID {} data length missmatch: dbc says {} but {} was supplied'.format(hex(self.mid), self.dbc_info[self.mid]['dlc']), len(data))
                    self.name = self.dbc_info[self.mid]['name']
                self.dlc = len(data)

                # padd data sequence up to 8 bytes
                if isinstance(data, list):
                    data += [0, ] * (8 - len(data))
                    if PY_VERSION == 3:
                        self._data = unpack('<Q', bytes(data))[0]
                    else:
                        self._data = unpack('<Q', ''.join([chr(e) for e in data]))[0]
                elif isinstance(data, bytes):
                    data += b'\x00' * (8 -len(data))
                    if PY_VERSION == 3:
                        self._data = unpack('<Q', data)[0]
                    else:
                        self._data = unpack('<Q', str(data))[0]
                elif isinstance(data, tuple):
                    data += (0, ) * (8 - len(data))
                    if PY_VERSION == 3:
                        self._data = unpack('<Q', bytes(data))[0]
                    else:
                        self._data = unpack('<Q', ''.join([chr(e) for e in data]))[0]
            else:
                if self.mid in self.dbc_info:
                    self.dlc = self.dbc_info[self.mid]['dlc']
                    self.name = self.dbc_info[self.mid]['name']
                    self._data = 0
                else:
                    if dlc is None:
                        raise USBtinException('CAN ID {} dlc unavailable: dlc or data must be supplied if no dbc was loaded'.format(hex(self.mid)))
                    else:
                        self.dlc = dlc
                        self._data = 0

    def __repr__(self):
        return '{} {}'.format(self.name, hex(self.mid))

    @staticmethod
    def load_dbc(dbc):
        ''' Loads all messages description from DBC. This information is later
        used for asttibute like access to message signals.

        Parameters
        ----------
        dbc : str
            DBC file path

        '''
        CANMessage.dbc_info.clear()

        pattern = r'(?P<msg>^BO_ (.+\n)+)'

        with open(dbc, 'r') as f:
            string = f.read()

        messages = {}

        for match in re.finditer(pattern, string, flags=re.M):
            msg = match.group('msg')

            pattern = r'BO_ (?P<can_id>\d+) (?P<name>[^ :]+): (?P<dlc>\d).+'
            match = re.search(pattern, msg)
            can_id = int(match.group('can_id'))
            name = match.group('name')
            dlc = int(match.group('dlc'))

            pattern = (r'SG_ (?P<name>[^ ]+) : '
                       r'(?P<start_bit>\d{1,2})\|(?P<size>\d{1,2})'
                       r'@(?P<byte_order>\d)(?P<signed>[+-])'
                       r' \((?P<factor>[^,]+),(?P<offset>[^)]+)\)'
                       r' \[(?P<min_value>[^|]+)\|(?P<max_value>[^]]+)\]'
                       r' "(?P<unit>[^"]*)"')

            messages[can_id] = {'name': name, 'dlc': dlc, 'signals': {}, 'can_id': can_id}

            signals = messages[can_id]['signals']

            for match in re.finditer(pattern, msg):
                signal_name = match.group('name')
                start_bit = int(match.group('start_bit'))
                size = int(match.group('size'))
                byte_order = match.group('byte_order')
                signed = match.group('signed') == '-'
                factor = float(match.group('factor'))
                offset = float(match.group('offset'))
                min_value = float(match.group('min_value'))
                max_value = float(match.group('max_value'))
                unit = match.group('unit')
                signals[signal_name] = {'start_bit': start_bit,
                                        'size': size,
                                        'byte_order': byte_order,
                                        'signed': signed,
                                        'factor': factor,
                                        'offset': offset,
                                        'min_value': min_value,
                                        'max_value': max_value,
                                        'unit': unit}

        CANMessage.dbc_info.update(messages)

    def __setattr__(self, name, value):
        if name in ('dbc_info', 'mid'):
            super(CANMessage, self).__setattr__(name, value)
        else:
            if self.mid in self.dbc_info:
                signals = self.dbc_info[self.mid]['signals']
                if name in signals:
                    sig = signals[name]

                    size = sig['size']
                    bit_offset = sig['start_bit']

                    value = int(value / sig['factor'] + sig['offset'])

                    mask = (2**size - 1) << bit_offset

                    value = (value << bit_offset) & mask

                    self._data = (self._data & (~mask)) + value
                else:
                    super(CANMessage, self).__setattr__(name, value)
            else:
                super(CANMessage, self).__setattr__(name, value)

    def __getattribute__(self, name):
        if name in ('dbc_info', 'mid'):
            return super(CANMessage, self).__getattribute__(name)
        else:
            dbc_info = super(CANMessage, self).__getattribute__('dbc_info')
            if self.mid in dbc_info:
                signals = dbc_info[self.mid]['signals']
                if name in signals:
                    sig = signals[name]

                    size = sig['size']
                    bit_offset = sig['start_bit']
                    factor = sig['factor']
                    offset = sig['offset']

                    mask = (2**size - 1) << bit_offset
                    value = (self._data & mask) >> bit_offset

                    if sig['signed']:
                        if value & (2**(size-1)):
                            value -= 2**size

                    if (factor, offset) == (1, 0):
                        return value
                    else:
                        return (value - offset) * factor

                else:
                    return super(CANMessage, self).__getattribute__(name)
            else:
                return super(CANMessage, self).__getattribute__(name)

    def __getitem__(self, index):
        if isinstance(index, int):
            if 0 <= index <= 7:
                shift = index * 8
                mask = 0xFF << shift
                return (self._data & mask) >> shift
            else:
                raise USBtinException('Index value error: the index must an integer between 0 and 7; {} given'.format(index))
        else:
            raise USBtinException('Index type error: the index must an integer between 0 and 7; "{}" of type "{}" gives'.format(index, type(index)))

    def __setitem__(self, index, value):
        if isinstance(index, int):
            if 0 <= index <= 7:
                shift = index * 8
                mask = 0xFF << shift
                value = (value << shift) & mask
                self._data = self._data & (~mask) | value
            else:
                raise USBtinException('Index value error: the index must an integer between 0 and 7; {} given'.format(index))
        else:
            raise USBtinException('Index type error: the index must an integer between 0 and 7; "{}" of type "{}" gives'.format(index, type(index)))

    def __iter__(self):
        # return (self[i] for i in range(self.dlc))
        if PY_VERSION == 3:
            return (b for b in pack('<Q', self._data)[:self.dlc])
        else:
            return (ord(b) for b in pack('<Q', self._data)[:self.dlc])

    @classmethod
    def from_string(cls, msg):
        """Create message with given message string.
        The message string is parsed. On errors, the corresponding value is set to zero.

        Example message strings:
           t1230        id: 123h        dlc: 0      data: --
           t00121122    id: 001h        dlc: 2      data: 11 22
           T12345678197 id: 12345678h   dlc: 1      data: 97
           r0037        id: 003h        dlc: 7      RTR

        Parameters
        ----------
        msg : str
            payload as string

        """
        rtr = False

        index = 1

        if msg:
            mtype = msg[0]
            data = []
            if mtype == 'r':
                mid = int(msg[index: index + 3], 16)
                dlc = int(msg[index + 3], 16)
                rtr = True
            elif mtype == 'R':
                mid = int(msg[index: index + 8], 16)
                dlc = int(msg[index + 8], 16)
                rtr = True
            elif mtype == 't':
                mid = int(msg[index: index + 3], 16)
                dlc = int(msg[index + 3], 16)
                index = index + 4
                for i in range(dlc):
                    data.append(int(msg[index: index + 2], 16))
                    index += 2
            elif mtype == 'T':
                mid = int(msg[index: index + 8], 16)
                dlc = int(msg[index + 8], 16)
                index = index + 8
                for i in range(dlc):
                    data.append(int(msg[index: index +1], 16))
                    index += 2
            return cls(mid, data=data, dlc=dlc, rtr=rtr)
        else:
            mid = 0
            dlc = 0
            return cls(mid, dlc=dlc)

    def get_data(self):
        """ Get CAN message payload data """
        return self.data

    def set_data(self, data):
        """Set CAN message payload data

           Keyword arguments:
           data -- Message data
        """
        self.data = data

    def is_extended(self):
        """ Determine if CAN message id is extended """
        return self.extended

    def is_rtr(self):
        """ Determine if CAN message is a request for transmission """
        return self.rtr

    def to_string(self):
        """ gets message command as string

        Returns
        -------
        s : str
            formated string command
        """

        s = ''
        if self.extended:
            if self.rtr:
                s += 'R'
            else:
                s += 'T'
            s += "{:08x}".format(self.mid)
        else:
            if self.rtr:
                s += 'r'
            else:
                s += 't'
            s += "{:03x}".format(self.mid)

        s += '{:01x}'.format(self.dlc)
        for b in pack('<Q', self._data)[:self.dlc]:
            if PY_VERSION == 3:
                s += "{:02x}".format(b)
            else:
                s += "{:02x}".format(ord(b))
        return s

    def __str__(self):
        s = "CAN message { id = 0x"
        if self.extended:
            s += "{:08x} (extended)".format(self.mid)
        else:
            s += "{:02x} ".format(self.mid)

        s += " len = {} ".format(self.dlc)

        if self.rtr:
            s += " RTR"
        else:
            s += "["
            for b in self:
                s += " {:02x}".format(b)
            s += " ]"
        s += "}"

        if self.mid in self.dbc_info:
            for signal in self.dbc_info[self.mid]['signals']:
                s += '\n\t{:>32} {}'.format(signal, getattr(self, signal))

        return s


if __name__ == "__main__":
    pass
