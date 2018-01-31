"""
Dwarf
~~~~~

Discord Web Application Rendering Framework

:copyright: (c) 2016-2018 Aileen Lumina et al.
:license: MIT, see LICENSE for more details.
"""

__title__ = 'Dwarf'
__author__ = 'Aileen Lumina et al.'
__license__ = 'MIT'
__copyright__ = 'Copyright 2016-2018 Aileen Lumina et al.'
__version__ = '0.11.0b'


from collections import namedtuple


VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')

version_info = VersionInfo(major=0, minor=11, micro=0, releaselevel='beta', serial=0)
