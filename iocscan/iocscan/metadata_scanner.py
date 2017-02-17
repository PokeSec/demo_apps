"""
metadata_scanner.py : Metadata scanner

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
import hashlib
import logging
import struct
import time
from io import BytesIO
from pathlib import Path
from typing import Tuple

from epclib.common.compressor import Compressor, Decompressor
from .indx_parser import FileIndex, KaitaiStream


class Indexer(object):
    def __init__(self):
        self.__changes = 0
        self.__old_index = dict()
        self.__index = dict()
        self.__index_path = Path('iocscan.index')
        if self.__index_path.exists():
            with self.__index_path.open('rb') as ifile:
                header = ifile.read(4)
                decompressor = Decompressor.from_header(header)
                self.__old_index = self.__parse_index(decompressor.decompress(ifile.read()))

    def __parse_index(self, data: bytes):
        out = dict()
        old_data = FileIndex(KaitaiStream(BytesIO(data)))
        for item in old_data.data:  # type: FileIndex.IndxData
            out[item.key] = {x: getattr(item, x) for x in dir(item) if
                             not x.startswith('_') and not callable(getattr(item, x))}
        return out

    def __get_key(self, data):
        return hashlib.sha1('{inode}{mtime}{path}'.format(**data).encode('utf-8')).digest()

    def in_index(self, data: dict):
        return self.__get_key(data) in self.__old_index

    def index(self, data: dict):
        key = self.__get_key(data)
        if key in self.__old_index:
            self.__index[key] = self.__old_index[key]
            del self.__old_index[key]
        else:
            self.__index[key] = data
            self.__changes += 1

    def write(self):
        self.__changes += len(self.__old_index)

        if self.__changes == 0:
            return

        with self.__index_path.open('wb') as ofile:
            # Raw data
            header, compressor = Compressor.get()
            ofile.write(header)

            # Start of compressed data
            header = b'SONEINDX'
            header += struct.pack('<B', 1)  # version
            header += struct.pack('<L', len(self.__index))  # count
            ofile.write(compressor.compress(header))

            for key, data in self.__index.items():
                indx_data = b''
                indx_data += key
                indx_data += data.get('mountpoint', '').encode('utf-8') + b'\0'
                indx_data += data.get('path', '').encode('utf-8') + b'\0'
                indx_data += data.get('ads', '').encode('utf-8') + b'\0'
                for hash_name in ['md5', 'sha1', 'sha256']:
                    hash_data = data.get(hash_name)
                    indx_data += hash_data.digest() if hash_data else b'0' * hashlib.new(hash_name).digest_size
                indx_data += struct.pack('<f', data.get('entropy', 0.0))  # entropy
                ofile.write(compressor.compress(indx_data))
            ofile.write(compressor.flush())


class MetadataScanner(object):
    def __init__(self, config):
        self.config = config
        # self.index = None

    def init(self):
        self.__indexer = Indexer()
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
        if not self.__can_scan(fobj):
            return

        for ads, stream in fobj.streams.items():
            if not ads or ads == '$Data':
                ads_txt = ''
            else:
                ads_txt = ':{}'.format(ads)

            obj_data = dict(
                mountpoint=mountpoint,
                path=fobj.path.as_posix(),
                ads=ads_txt,
            )
            obj_data.update(stream)

            if not self.__indexer.in_index(obj_data):
                # Perform heavy computation only if the object has changed
                if stream['size'] < self.config.get('MAX_SIZE', 256) * 1024 * 1024:
                    hashes = fobj.get_hashes(ads)
                else:
                    hashes = dict()
                obj_data.update(hashes)

            self.__indexer.index(obj_data)

    def finalize(self) -> Tuple[dict, list]:
        self.__indexer.write()
        exec_time = time.perf_counter() - self.perf1
        logging.info("Indexed in %s", exec_time)
        return dict(), []
