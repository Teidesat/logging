#
# Autogenerated by Thrift Compiler (0.11.0)
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
#  options string: py
#

from thrift.Thrift import TType, TMessageType, TFrozenDict, TException, TApplicationException
from thrift.protocol.TProtocol import TProtocolException
from thrift.TRecursive import fix_spec

import sys

from thrift.transport import TTransport
all_structs = []


class TempData(object):
    """
    Attributes:
     - temp
     - sensor_id
     - timestamp
    """


    def __init__(self, temp=None, sensor_id=None, timestamp=None,):
        self.temp = temp
        self.sensor_id = sensor_id
        self.timestamp = timestamp

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 1:
                if ftype == TType.DOUBLE:
                    self.temp = iprot.readDouble()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRING:
                    self.sensor_id = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.I64:
                    self.timestamp = iprot.readI64()
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot._fast_encode is not None and self.thrift_spec is not None:
            oprot.trans.write(oprot._fast_encode(self, [self.__class__, self.thrift_spec]))
            return
        oprot.writeStructBegin('TempData')
        if self.temp is not None:
            oprot.writeFieldBegin('temp', TType.DOUBLE, 1)
            oprot.writeDouble(self.temp)
            oprot.writeFieldEnd()
        if self.sensor_id is not None:
            oprot.writeFieldBegin('sensor_id', TType.STRING, 2)
            oprot.writeString(self.sensor_id.encode('utf-8') if sys.version_info[0] == 2 else self.sensor_id)
            oprot.writeFieldEnd()
        if self.timestamp is not None:
            oprot.writeFieldBegin('timestamp', TType.I64, 3)
            oprot.writeI64(self.timestamp)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)
all_structs.append(TempData)
TempData.thrift_spec = (
    None,  # 0
    (1, TType.DOUBLE, 'temp', None, None, ),  # 1
    (2, TType.STRING, 'sensor_id', 'UTF8', None, ),  # 2
    (3, TType.I64, 'timestamp', None, None, ),  # 3
)
fix_spec(all_structs)
del all_structs
