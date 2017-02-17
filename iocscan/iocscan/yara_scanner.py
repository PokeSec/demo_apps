"""
yara_scanner.py : Yara scanner

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
import io
import logging
import time
import yara
from typing import Tuple

from epc.common.data import DataClient
from epc.common.data.client import DataException
from epc.common.exceptions import DataError


class YaraScanner(object):
    def __init__(self, config):
        self.yara_rules = []
        self.config = config

        self.scan_count = 0
        self.detect_count = 0
        self.report = []

    def init(self):
        try:
            data = DataClient().get('http_blob', self.config.get('RULES_FILE'))
            if not data:
                logging.error("Cannot get rules %s", self.config.get('RULES_FILE'))
                return 1
        except (DataException, DataError):
            logging.error('Cannot get rules %s', self.config.get('RULES_FILE'))
            return 1
        rules = io.BytesIO(data)

        try:
            self.yara_rules.append(yara.load(file=rules))
        except yara.Error:
            logging.error("Cannot load rules %s", self.config.get('RULES_FILE'))
            return 1

        logging.info("%d signatures loaded" % len(self.yara_rules))
        self.perf1 = time.perf_counter()

    def __can_scan(self, item):
        if item.is_directory():
            return False
        if not not self.config["INCLUDE_DELETED"] and item.is_deleted():
            return False
        if self.config.get('SCAN_EXTENSIONS') and item.path.suffix.lower() not in self.config.get('SCAN_EXTENSIONS'):
            return False
        if item.path.name in self.config.get('EXCLUDE_FILES', []):
            return False
        return True

    def process(self, mountpoint, fobj):
        if self.__can_scan(fobj):
            for ads, stream in fobj.streams.items():
                if stream['size'] < self.config.get('MAX_SIZE') * 1024 * 1024:
                    if not ads or ads == '$Data':
                        logging.debug("%s%s",
                                      fobj.path,
                                      u" (deleted)" if fobj.is_deleted() else u"")
                    else:
                        logging.debug("%s:%s%s",
                                      fobj.path,
                                      ads,
                                      " (deleted)" if fobj.is_deleted() else u"")
                    matches = fobj.scan_yara(self.yara_rules, ads,
                                             self.config.get("YARA_FASTSCAN_MODE", True))
                    self.scan_count += 1

                    if matches:
                        self.detect_count += len(matches)
                        report_data = dict(
                            extra=self.config.get("task_id", None),
                            filepath=str(fobj.path),
                            md5=fobj.get_hash_md5(ads),
                            sha1=fobj.get_hash_sha1(ads),
                            sha256=fobj.get_hash_sha256(ads),
                            entropy=fobj.get_entropy(ads),
                            timestamp=self.config.get('timestamp')
                        )
                        if fobj.is_deleted():
                            report_data["deleted"] = True
                        for match in matches:
                            report_data['rule'] = '{}:{}'.format(match.namespace, match.rule)
                            self.report.append(report_data)

    def finalize(self) -> Tuple[dict, list]:
        exec_time = time.perf_counter() - self.perf1
        final_report = dict(
            extra=self.config.get("task_id", None),
            rules=self.config.get('RULES_FILE'),
            exec_time=exec_time,
            scan_count=self.scan_count,
            detect_count=self.detect_count,
            timestamp=self.config.get('timestamp')
        )
        logging.info("Scan completed %s", final_report)
        return final_report, self.report
