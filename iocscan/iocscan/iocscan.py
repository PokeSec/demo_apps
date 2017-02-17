"""
iocscan.py : IOC scanning App

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

from pathlib import Path

import arrow

from epc.common.data import DataClient
from epc.common.settings import Config
from epclib.common.iapp import App
from epclib.filesystem.drive import DriveManager
from .metadata_scanner import MetadataScanner
from .yara_scanner import YaraScanner

DEFAULT_CONFIGS = dict(
    win32=dict(
        MAX_SIZE=256,
        SCAN_ROOTS=None,
        SCAN_EXTENSIONS=['.exe', '.dll', '.sys', '.scr'],
        EXCLUDE_FILES=['pagefile.sys', 'hiberfil.sys', 'swapfile.sys'],
        EXCLUDE_DIRS=[],
        RULES_FILE='yara_rules',
        REPORTING_MODE='standard',
        INCLUDE_DELETED=False
    ),
    unix=dict(
        MAX_SIZE=256,
        SCAN_ROOTS=None,
        EXCLUDE_FILES=[],
        EXCLUDE_DIRS=[
            '/proc', '/run', '/dev',
            '.git'],
        RULES_FILE='yara_rules',
        REPORTING_MODE='standard',
        INCLUDE_DELETED=False
    ),
    android=dict(
        MAX_SIZE=256,
        SCAN_ROOTS=['/system', '/sdcard'],
        EXCLUDE_FILES=[],
        EXCLUDE_DIRS=[
            '/proc', '/run', '/dev',
            '/sdcard/DCIM', '/sdcard/Android'],
        RULES_FILE='yara_rules',
        REPORTING_MODE='standard',
        INCLUDE_DELETED=False
    )
)


class IocScanApp(App):
    """Simple IOC Scanning app (match yara rules on interesting exts)"""

    def __init__(self, platform):
        super().__init__()
        self.cur_data = None
        self.cur_data_pos = 0
        self.config = DEFAULT_CONFIGS.get(platform)
        self.report = []
        self.state = dict()
        self.scanners = []

    def __recursion_callback(self, item: Path):
        posix_path = item.as_posix()
        path = posix_path[3:] if Config().PLATFORM == 'win32' and posix_path[1] == ':' else posix_path
        for excl in self.config.get('EXCLUDE_DIRS'):
            if path.startswith(excl):
                return False
        return True

    def _run(self, *args, **kwargs) -> int:
        self.config.update({k: v for k, v in kwargs.get('config', {}).items() if v})
        self.config['timestamp'] = arrow.utcnow().isoformat()

        self.logger.debug("IOCScan running with %s", self.config)

        scan_classes = [
            YaraScanner,
            MetadataScanner
        ]

        drivemanager = DriveManager()

        for scan_class in scan_classes:
            scanner = scan_class(self.config)
            scanner.init()
            self.scanners.append(scanner)

        for drivepath, mountpoint in drivemanager.list_available():
            try:
                self.logger.info("Scanning %s | %s", drivepath, mountpoint)
                drive = drivemanager.open(drivepath, mountpoint)
                for fobj in drive.enumerate_files(directory=self.config["SCAN_ROOTS"],
                                                  recurse_callback=self.__recursion_callback):
                    for scanner in self.scanners:
                        scanner.process(mountpoint, fobj)

            except Exception as exc:
                self.logger.debug("Cannot scan %s | %s : %s", drivepath, mountpoint, exc)

        for scanner in self.scanners:
            state, report = scanner.finalize()
            self.report += report
            self.state.update(state)

        self.__send_report()
        self.__send_state()

        self.logger.info("IOCScan done")
        return 0

    def __send_report(self):
        report_mode = 'report_{}'.format(self.config.get('REPORTING_MODE', 'standard'))
        if not DataClient().send(report_mode, 'iocscan_report', self.report):
            self.logger.error("Could not send IOCScan report")
        DataClient().flush(report_mode)

    def __send_state(self):
        report_mode = 'report_state'
        if not DataClient().send(report_mode, 'iocscan', self.state):
            self.logger.error("Could not send IOCScan state")
        DataClient().flush(report_mode)

    def _stop(self):
        self.logger.info("IOCScan STOP")


def app_factory(platform=None):
    """Get the appropriate app"""
    return IocScanApp(platform)


APPCLASS = app_factory
