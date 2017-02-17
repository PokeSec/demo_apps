"""
iocscan.py : Simple IOC scanning App

This file is part of EPControl.

Copyright (C) 2016  Jean-Baptiste Galet & Timothe Aeberhardt

EPControl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

EPControl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with EPControl.  If not, see <http://www.gnu.org/licenses/>.
"""

from epc.common.data import DataClient
from epc.common.data.client import DataException
from epclib.common.iapp import App
from epclib.common.platform import PlatformInfo


class MetadataApp(App):
    """Collect metadata about the platform"""

    def __init__(self):
        super().__init__()
        self.config = dict(
            REPORTING_MODE='standard',
            FULL=False,
            PLATFORM=True,
            CPU=True,
            MEMORY=True,
            DISK=True,
            NETWORK=True,
            BOOT_TIME=True,
            USER=True,
            PROCESS=True,
            SOFTWARE=True,
            WINSERVICE=True
        )

    def _run(self, *args, **kwargs):
        self.config.update(kwargs.get('config', {}))
        if self.config['FULL']:
            level = PlatformInfo.Level.full
        else:
            level = PlatformInfo.Level.basic

        types = []
        for data_type, enabled in self.config.items():
            if enabled and data_type not in ('REPORTING_MODE', 'FULL'):
                types.append(data_type.lower())

        data = PlatformInfo().get_data(level, types)

        ret = 0
        for k, v in data.items():
            try:
                DataClient().send('report_standard', 'metadata_{}_report'.format(k), v)
            except DataException:
                self.logger.error("Could not send metadata")
                ret = 1
            DataClient().flush('report_standard')
        return ret

    def _stop(self):
        pass


def app_factory(platform=None):
    """Get the appropriate app"""
    return MetadataApp()


APPCLASS = app_factory
