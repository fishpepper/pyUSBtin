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


# this class represents a can filtermask
class FilterMask(object):
    def __init__(self, extid):
        """ Create filter mask for extended CAN messages.

           Keyword arguments:
            extid -- Filter mask for CAN identifier

           Notes:
            Bitmask:
            0 - accept (accept regardless of filter)
            1 - check (accept only if filter matches)

           Examples:
            fm1 = FilterMask(0x1fffffff) # Check whole extended id
            fm2 = FilterMask(0x1fffff00) # Check extended id except last 8 bits
        """
        self.registers = []
        self.registers[0] = ((extid >> 21) & 0xff)
        self.registers[1] = (((extid >> 16) & 0x03) | ((extid >> 13) & 0xe0))
        self.registers[2] = ((extid >> 8) & 0xff)
        self.registers[3] = (extid & 0xff)

    def __init__(self, sid, d0, d1):
        """ Create filter mask for standard CAN messages.

            Keyword arguments:
             sid -- Filter mask for CAN identifier
             d0 -- Filter mask for first data byte
             d1 -- Filter mask for second data byte

            Bitmask:
             0 - accept (accept regardless of filter)
             1 - check (accept only if filter matches)

            Examples:
             fm1 = FilterMask(0x7ff, (byte)0x00, (byte)0x00) # check whole id, data bytes are irrelevant
             fm2 = FilterMask(0x7f0, (byte)0x00, (byte)0x00) # check whole id except last 4 bits,
                                                             # data bytes are irrelevant
             fm2 = FilterMask(0x7f0, (byte)0xff, (byte)0x00) # check whole id except last 4 bits,
                                                             # check first data byte, second is irrelevant
        """
        self.registers = []
        self.registers[0] = ((sid >> 3) & 0xff)
        self.registers[1] = ((sid & 0x7) << 5)
        self.registers[2] = d0
        self.registers[3] = d1

    def get_registers(self):
        """Get register values in MCP2515 style"""
        return self.registers
