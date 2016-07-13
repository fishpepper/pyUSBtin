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


# this class represents a can filterchain
class FilterChain(object):
    def __init__(self, mask, filters):
        """ Create filter chain with one mask and filters.

           Keyword arguments:
            mask -- Mask
            filters -- Filters
        """
        self.mask = mask
        self.filters = filters

    def get_mask(self):
        """ Get mask of this filter chain."""
        return self.mask

    def get_filters(self):
        """Get filters of this filter chain."""
        return self.filters
