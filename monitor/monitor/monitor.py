"""
monitor.py : Simple Monitoring App

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
from functools import partial

from epc.common.data import DataClient
from epc.common.settings import Config
from epclib.common.iapp import App
from epclib.event.event import Event

DEFAULT_CONFIGS = dict(
    win32=dict(
        ADVANCED=False,
        REPORTING_MODE='standard',
        SEND_THRESHOLD=100,
    ),
    unix=dict(
        ADVANCED=False,
        REPORTING_MODE='standard',
        SEND_THRESHOLD=100,
    ),
    android=dict(
        ADVANCED=False,
        REPORTING_MODE='standard',
        SEND_THRESHOLD=1,
    )
)


class MonitorApp(App):
    def __init__(self, platform=None):
        super(MonitorApp, self).__init__()

        self.report = []
        self.config = DEFAULT_CONFIGS.get(platform, dict())

        if Config().PLATFORM == 'unix':
            from epclib.event.linevt import LinuxEventMonitor
            self.monitor = LinuxEventMonitor()
        elif Config().PLATFORM == 'android':
            from epclib.event.androidevt import AndroidEventMonitor
            self.monitor = AndroidEventMonitor()
        elif Config().PLATFORM == 'win32':
            from epclib.event.winevt import WinEventMonitor
            self.monitor = WinEventMonitor()
        else:
            raise NotImplementedError()

        for event in Event:
            self.monitor.add_callback(event, partial(self.event_cb, event))

    def _run(self, *args, **kwargs):
        self.monitor.run()
        return 1  # Never cache execution

    def _stop(self):
        self.monitor.stop()
        self.__send_report()

    def event_cb(self, event: Event, **kwargs):
        # FIXME: Log Unknown process launching, uncommon child, crashes, debugged, owner changed (reputation based)
        self.logger.debug("Caught event %s with args %s", event, kwargs)

        data = dict(
            subtype=event.name,
            extra=self.config.get("task_id", None)
        )
        data.update(kwargs)

        self.report.append(data)
        if len(self.report) > self.config.get('SEND_THRESHOLD', 100):
            self.__send_report()

    def __send_report(self):
        report_mode = 'report_{}'.format(self.config.get('REPORTING_MODE', 'standard'))
        if not DataClient().send(report_mode, 'monitor_report', self.report):
            self.logger.error("Could not send report")
        else:
            DataClient().flush(report_mode)
            self.report = []


APPCLASS = MonitorApp


def main():
    """Test function"""
    import threading
    import logging
    import time
    app = MonitorApp()
    app.logger = logging
    t = threading.Thread(target=app._run)
    t.start()
    time.sleep(5)
    app._stop()
    t.join()
