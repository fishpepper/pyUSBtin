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


# this class represents a can message
class CANMessage(object):
    def __init__(self, mid, data, extended=None, rtr=None):
        """Create message with given message properties.

           if extended is not given, extended flag is extracted from id

           Keyword arguments:
           id -- id Message identifier
           data -- Payload data
           extended -- Marks messages with extended identifier
           rtr -- Marks RTR messages
        """
        self.mid = 0
        self.rtr = False
        self.extended = False

        self.set_id(mid)
        self.data = data
        if extended is not None:
            self.extended = extended
        if rtr is not None:
            self.rtr = rtr

    @classmethod
    def from_string(cls, msg):
        """Create message with given message string.
           The message string is parsed. On errors, the corresponding value is set to zero.

           Keyword arguments:
           string -- payload as string

           Example message strings:
           t1230        id: 123h        dlc: 0      data: --
           t00121122    id: 001h        dlc: 2      data: 11 22
           T12345678197 id: 12345678h   dlc: 1      data: 97
           r0037        id: 003h        dlc: 7      RTR
        """
        rtr = False

        index = 1
        mtype = 't' if (len(msg) <= 0) else msg[0]

        # extract type & id
        if mtype in 'RT':
            if mtype == 'R':
                rtr = True
            try:
                mid = int(msg[index:index + 8], 16)
            except ValueError:
                mid = 0

            extended = True
            index += 8
        else:
            if mtype == 'r':
                rtr = True
            try:
                mid = int(msg[index:index + 3], 16)
            except ValueError:
                mid = 0

            extended = False
            index += 3

        # extract length
        try:
            length = int(msg[index:index + 1], 16)
        except ValueError:
            length = 0
        index += 1

        # extract data
        data = []
        if not rtr:
            for i in range(length):
                try:
                    data.append(int(msg[index:index + 2], 16))
                except ValueError:
                    data.append(0)
                index += 2
        return cls(mid, data, extended, rtr)

    def get_id(self):
        """ Get CAN message identifier """
        return self.mid

    def set_id(self, mid):
        """Set CAN message identifier

           Keyword arguments:
           id -- id Message identifier
        """
        if mid > 0x1fffffff:
            mid = 0x1fffffff

        if mid > 0x7ff:
            self.extended = True

        self.mid = mid

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
        s = ""
        if self.extended:
            if self.rtr:
                s += 'R'
            else:
                s += 'T'
            s += "%0.8x" % self.mid
        else:
            if self.rtr:
                s += 'r'
            else:
                s += 't'
            s += "%0.3x" % self.mid
        s += "%01X" % len(self.data)

        if not self.rtr:
            for x in self.data:
                s += "%02x" % ord(x)

        return s

    def __str__(self):
        s = "CAN message {"
        s += " id = 0x"
        if self.extended:
            s += "%08x (extended)" % self.mid
        else:
            s += "%02x " % self.mid

        s += " len = %d " % len(self.data)

        if self.rtr:
            s += " RTR"
        else:
            s += "["
            for x in self.data:
                s += " %02x" % x
            s += "]"
        s += "}"

        return s


if __name__ == "__main__":
    # do a simple test:
    print(CANMessage.from_string("T12345678197").to_string())
    print(CANMessage.from_string("T12345678197"))
    print(CANMessage.from_string("t00121122").to_string())
    print(CANMessage.from_string("t00121122"))
