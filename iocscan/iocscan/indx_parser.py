# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import array
import struct
import zlib
from enum import Enum

from epc.common.kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


class FileIndex(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self.header = self._root.IndxHeader(self._io, self, self._root)
        self.data = [None] * (self.header.count)
        for i in range(self.header.count):
            self.data[i] = self._root.IndxData(self._io, self, self._root)


    class IndxHeader(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.magic = self._io.ensure_fixed_contents(8, struct.pack('8b', 83, 79, 78, 69, 73, 78, 68, 88))
            self.version = self._io.read_u1()
            self.count = self._io.read_u4le()


    class IndxData(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.key = self._io.read_bytes(20)
            self.mountpoint = self._io.read_strz("UTF-8", 0, False, True, True)
            self.path = self._io.read_strz("UTF-8", 0, False, True, True)
            self.ads = self._io.read_strz("UTF-8", 0, False, True, True)
            self.md5 = self._io.read_bytes(16)
            self.sha1 = self._io.read_bytes(20)
            self.sha256 = self._io.read_bytes(32)
            self.entropy = self._io.read_f4le()



