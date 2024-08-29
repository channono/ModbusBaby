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

class ByteOrder(Enum):
    BIG_ENDIAN = 'big'
    LITTLE_ENDIAN = 'little'

class WordOrder(Enum):
    BIG_ENDIAN = 'big'
    LITTLE_ENDIAN = 'little'

class DataProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_data(self, raw_value, data_type, unit):
        try:
            converted_value = self._convert_data_type(raw_value, data_type)
            return self._apply_unit_conversion(converted_value, unit)
        except Exception as e:
            self.logger.error(f"处理数据时发生错误: {e}")
            return None

    def _convert_data_type(self, raw_value, data_type):
        if isinstance(raw_value, list):
            raw_value = raw_value[0] if len(raw_value) == 1 else raw_value

        if data_type == DataType.INT16.value:
            return self._to_int16(raw_value)
        elif data_type == DataType.UINT16.value:
            return self._to_uint16(raw_value)
        elif data_type == DataType.INT32.value:
            return self._to_int32(raw_value)
        elif data_type == DataType.UINT32.value:
            return self._to_uint32(raw_value)
        elif data_type == DataType.FLOAT32.value:
            return self._to_float32(raw_value)
        elif data_type == DataType.BOOL.value:
            return bool(raw_value)
        elif data_type == DataType.FLOAT64.value:
            return self._to_float64(raw_value)
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")

    def _to_int16(self, value):
        return struct.unpack('>h', struct.pack('>H', value))[0]

    def _to_uint16(self, value):
        return value

    def _to_int32(self, value):
        if isinstance(value, list) and len(value) == 2:
            return struct.unpack('>i', struct.pack('>HH', value[0], value[1]))[0]
        raise ValueError("INT32 需要两个 16 位寄存器值")

    def _to_uint32(self, value):
        if isinstance(value, list) and len(value) == 2:
            return (value[0] << 16) | value[1]
        raise ValueError("UINT32 需要两个 16 位寄存器值")

    def _to_float32(self, value):
        if isinstance(value, list) and len(value) == 2:
            return struct.unpack('>f', struct.pack('>HH', value[0], value[1]))[0]
        raise ValueError("FLOAT32 需要两个 16 位寄存器值")

    def _to_float64(self, value):
        if isinstance(value, list) and len(value) == 4:
            return struct.unpack('>d', struct.pack('>HHHH', value[0], value[1], value[2], value[3]))[0]
        raise ValueError("FLOAT64 需要四个 16 位寄存器值")

    def _apply_unit_conversion(self, value, unit):
        # 这里可以实现单位转换逻辑
        # 例如,如果单位是 "kW",可以将 W 转换为 kW
        if unit.lower() == 'kw':
            return value / 1000
        # 添加更多单位转换逻辑...
        return value

    def format_value(self, value, data_type, decimal_places=2):
        if data_type in [DataType.FLOAT32.value]:
            return f"{value:.{decimal_places}f}"
        elif data_type in [DataType.INT16.value, DataType.UINT16.value, DataType.INT32.value, DataType.UINT32.value]:
            return f"{value:d}"
        elif data_type == DataType.BOOL.value:
            return str(value)
        else:
            return str(value)

    def value_to_registers(self, value, data_type, byte_order=ByteOrder.BIG_ENDIAN, word_order=WordOrder.BIG_ENDIAN):
        try:
            if data_type == DataType.FLOAT32.value:
                return self._float_to_registers(value, '>f', byte_order, word_order)
            elif data_type == DataType.FLOAT64.value:
                return self._float_to_registers(value, '>d', byte_order, word_order)
            elif data_type in [DataType.INT16.value, DataType.UINT16.value]:
                return [int(value) & 0xFFFF]
            elif data_type in [DataType.INT32.value, DataType.UINT32.value]:
                return self._int32_to_registers(int(value), byte_order)
            elif data_type == DataType.BOOL.value:
                return [1 if value else 0]
            else:
                raise ValueError(f"不支持的数据类型: {data_type}")
        except Exception as e:
            self.logger.error(f"转换值到寄存器时发生错误: {e}")
            raise

    def _float_to_registers(self, value, pack_format, byte_order, word_order):
        pack_format = pack_format if byte_order == ByteOrder.BIG_ENDIAN else pack_format.lower()
        bytes_value = struct.pack(pack_format, value)
        
        if word_order == WordOrder.LITTLE_ENDIAN:
            bytes_value = b''.join(reversed([bytes_value[i:i+2] for i in range(0, len(bytes_value), 2)]))
        
        return [int.from_bytes(bytes_value[i:i+2], byteorder='big') for i in range(0, len(bytes_value), 2)]

    def _int32_to_registers(self, value, byte_order):
        bytes_value = value.to_bytes(4, byteorder='big' if byte_order == ByteOrder.BIG_ENDIAN else 'little', signed=value < 0)
        return [int.from_bytes(bytes_value[i:i+2], byteorder='big') for i in range(0, 4, 2)]










