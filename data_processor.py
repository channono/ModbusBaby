import struct
import logging
from enum import Enum

class DataType(Enum):
    INT16 = 'INT16'
    UINT16 = 'UINT16'
    INT32 = 'INT32'
    UINT32 = 'UINT32'
    FLOAT32 = 'FLOAT32'
    FLOAT64 = 'FLOAT64'
    BOOL = 'BOOL'
    BYTE = 'BYTE' # Add BYTE here

class ByteOrder(Enum):
    BIG_ENDIAN = 'big'
    LITTLE_ENDIAN = 'little'

class WordOrder(Enum):
    BIG_ENDIAN = 'big'
    LITTLE_ENDIAN = 'little'

class DataProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # All other methods are now handled in modbus_debugger.py
    # This class is kept for future use if complex, non-modbus-related
    # data processing is needed.
    pass










