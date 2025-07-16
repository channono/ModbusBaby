#大牛大巨婴
import logging
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.pdu import ExceptionResponse
import serial
import os
from datetime import datetime

try:
    from serial.tools import list_ports
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False

class SocketWrapper:
    """ A wrapper for a socket object to intercept send/recv calls. """
    def __init__(self, sock, debugger):
        self._sock = sock
        self._debugger = debugger

    def send(self, data):
        self._debugger.last_sent_packet = data
        return self._sock.send(data)

    def recv(self, size):
        data = self._sock.recv(size)
        self._debugger.last_received_packet = data
        return data

    def __getattr__(self, name):
        """ Pass any other attribute requests to the underlying socket. """
        return getattr(self._sock, name)

class SerialWrapper:
    """ A wrapper for a serial object to intercept write/read calls. """
    def __init__(self, ser, debugger):
        self._ser = ser
        self._debugger = debugger

    def write(self, data):
        self._debugger.last_sent_packet = data
        return self._ser.write(data)

    def read(self, size):
        data = self._ser.read(size)
        self._debugger.last_received_packet = data
        return data

    def __getattr__(self, name):
        """ Pass any other attribute requests to the underlying serial object. """
        return getattr(self._ser, name)

class ModbusDebugger:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.client = None
        self.last_sent_packet = b''
        self.last_received_packet = b''
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.current_log_file = None
        self.packet_count = 0
        self.max_packets_per_file = 256

        # Store connection parameters
        self._connection_type = None
        self._connection_params = {}
        self._slave_id = None

    def get_available_serial_ports(self):
        if not PYSERIAL_AVAILABLE:
            self.logger.warning("pyserial 库未安装，无法获取可用串口列表")
            return []
        try:
            ports = list(list_ports.comports())
            return [port.device for port in ports]
        except Exception as e:
            self.logger.error(f"获取串口列表时发生错误: {str(e)}")
            return []

    def _wrap_client_socket(self):
        """ Wraps the client's socket to intercept packets. """
        if not self.client:
            return
        if isinstance(self.client, ModbusTcpClient) and self.client.socket:
            self.client.socket = SocketWrapper(self.client.socket, self)
        elif isinstance(self.client, ModbusSerialClient) and self.client.socket:
            self.client.socket = SerialWrapper(self.client.socket, self)

    def _reconnect(self):
        self.logger.info("尝试重新连接 Modbus 设备...")
        if self.client:
            self.client.close()
            self.client = None

        if self._connection_type == "tcp":
            return self.connect_tcp(
                self._connection_params['host'],
                self._connection_params['port'],
                self._slave_id
            )
        elif self._connection_type == "rtu":
            return self.connect_rtu(
                self._connection_params['port'],
                self._connection_params['baud_rate'],
                self._connection_params['data_bits'],
                self._connection_params['stop_bits'],
                self._connection_params['parity'],
                self._slave_id
            )
        return False

    def connect_tcp(self, host, port, slave_id):
        try:
            self.client = ModbusTcpClient(host=host, port=port)
            self._slave_id = slave_id
            self._connection_type = "tcp"
            self._connection_params = {'host': host, 'port': port}
            if self.client.connect():
                self._wrap_client_socket()
                return True
            return False
        except Exception as e:
            self.logger.error(f"TCP 连接失败: {str(e)}")
            return False

    def connect_rtu(self, port, baud_rate, data_bits, stop_bits, parity, slave_id):
        try:
            self.client = ModbusSerialClient(
                port=port,
                baudrate=baud_rate,
                bytesize=data_bits,
                parity=parity[0].upper(),
                stopbits=stop_bits
            )
            self._slave_id = slave_id
            self._connection_type = "rtu"
            self._connection_params = {
                'port': port,
                'baud_rate': baud_rate,
                'data_bits': data_bits,
                'stop_bits': stop_bits,
                'parity': parity
            }
            if self.client.connect():
                self._wrap_client_socket()
                return True
            return False
        except Exception as e:
            self.logger.error(f"RTU 连接失败: {str(e)}")
            return False

    def disconnect(self):
        if self.client:
            self.client.close()
            self.logger.info("已断开连接")

    def write_coils(self, address, values, slave_id=None):
        if not self.client:
            self.logger.error("未连接到设备")
            return False, "未连接", ("", "")
        for attempt in range(2): # Allow one retry
            try:
                self.last_sent_packet = b''
                self.last_received_packet = b''
                result = self.client.write_coils(address, values, slave=slave_id or self._slave_id)
                sent = self.format_packet(self.last_sent_packet)
                received = self.format_packet(self.last_received_packet)
                if isinstance(result, (ModbusIOException, ExceptionResponse)):
                    self.logger.error(f"写入多个线圈失败: {result}")
                    if attempt == 0 and self._reconnect():
                        continue # Retry after successful reconnect
                    return False, str(result), (sent, received)
                return True, "写入成功", (sent, received)
            except ModbusIOException as e:
                self.logger.error(f"写入多个线圈时发生 ModbusIOException: {e}")
                if attempt == 0 and self._reconnect():
                    continue # Retry after successful reconnect
                return False, str(e), (self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet))
            except Exception as e:
                self.logger.error(f"写入多个线圈时发生错误: {str(e)}")
                return False, str(e), (self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet))

    def write_registers(self, address, values, slave_id=None, data_type='UINT16', byte_order='big', word_order='big'):
        if not self.client:
            self.logger.error("未连接到设备")
            return False, "未连接", ("", "")
        
        from pymodbus.payload import BinaryPayloadBuilder
        from pymodbus.constants import Endian

        byteorder_map = {'big': Endian.BIG, 'little': Endian.LITTLE}
        wordorder_map = {'big': Endian.BIG, 'little': Endian.LITTLE}

        builder = BinaryPayloadBuilder(
            byteorder=byteorder_map[byte_order],
            wordorder=wordorder_map[word_order]
        )

        # Dynamically call the correct builder method based on data_type
        for value in values:
            if data_type == 'INT16':
                builder.add_16bit_int(value)
            elif data_type == 'UINT16':
                builder.add_16bit_uint(value)
            elif data_type == 'INT32':
                builder.add_32bit_int(value)
            elif data_type == 'UINT32':
                builder.add_32bit_uint(value)
            elif data_type == 'INT64':
                builder.add_64bit_int(value)
            elif data_type == 'UINT64':
                builder.add_64bit_uint(value)
            elif data_type == 'FLOAT32':
                builder.add_32bit_float(value)
            elif data_type == 'FLOAT64':
                builder.add_64bit_float(value)
            elif data_type == 'ASCII':
                 builder.add_string(value)
            # Note: BYTE and BOOL are handled as lists of UINT16s/Coils, not here.

        registers_to_write = builder.to_registers()

        for attempt in range(2): # Allow one retry
            try:
                self.last_sent_packet = b''
                self.last_received_packet = b''
                
                result = self.client.write_registers(address, registers_to_write, slave=slave_id or self._slave_id)
                sent = self.format_packet(self.last_sent_packet)
                received = self.format_packet(self.last_received_packet)

                if isinstance(result, (ExceptionResponse, ModbusIOException)):
                    self.logger.error(f"写入寄存器失败: {result}")
                    if attempt == 0 and self._reconnect():
                        continue # Retry after successful reconnect
                    return False, str(result), (sent, received)
                return True, "写入成功", (sent, received)
            except ModbusIOException as e:
                self.logger.error(f"写入寄存器时发生 ModbusIOException: {e}")
                if attempt == 0 and self._reconnect():
                    continue # Retry after successful reconnect
                return False, str(e), (self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet))
            except Exception as e:
                self.logger.error(f"写入寄存器时发生错误: {str(e)}")
                return False, str(e), (self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet))

    def _read_registers(self, address, count, slave_id, data_type, read_func, byte_order, word_order):
        if not self.client: return None, "", ""
        for attempt in range(2): # Allow one retry
            try:
                self.last_sent_packet = b''
                self.last_received_packet = b''
                result = read_func(address=address, count=count, slave=slave_id or self._slave_id)
                sent = self.format_packet(self.last_sent_packet)
                received = self.format_packet(self.last_received_packet)
                if isinstance(result, (ModbusIOException, ExceptionResponse)):
                    self.logger.error(f"读取寄存器失败: {result}")
                    if attempt == 0 and self._reconnect():
                        continue # Retry after successful reconnect
                    return None, sent, received
                
                processed_result = self.process_data(result.registers, data_type, byte_order, word_order)
                return processed_result, sent, received
            except ModbusIOException as e:
                self.logger.error(f"读取寄存器时发生 ModbusIOException: {e}")
                if attempt == 0 and self._reconnect():
                    continue # Retry after successful reconnect
                return None, self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet)
            except Exception as e:
                self.logger.error(f"读取寄存器时发生错误: {str(e)}")
                return None, self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet)

    def _read_bits(self, address, count, slave_id, read_func):
        if not self.client: return None, "", ""
        try:
            self.last_sent_packet = b''
            self.last_received_packet = b''
            # Explicitly name arguments to avoid positional argument confusion
            result = read_func(address=address, count=count, slave=slave_id or self.slave_id)
            sent = self.format_packet(self.last_sent_packet)
            received = self.format_packet(self.last_received_packet)
            if isinstance(result, ExceptionResponse):
                return None, sent, received
            return result.bits, sent, received
        except Exception as e:
            self.logger.error(f"读取位时发生错误: {str(e)}")
            return None, self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet)

    def format_packet(self, packet: bytes) -> str:
        if not isinstance(packet, bytes):
            return str(packet)
        return ' '.join(f'{b:02X}' for b in packet)

    def process_data(self, registers, data_type, byte_order='big', word_order='big'):
        try:
            if not registers: return []

            from pymodbus.payload import BinaryPayloadDecoder
            from pymodbus.constants import Endian

            byteorder_map = {'big': Endian.BIG, 'little': Endian.LITTLE}
            
            # Manual word swapping for multi-register values
            if word_order == 'little':
                num_regs_per_val = 1
                if data_type in ['INT32', 'UINT32', 'FLOAT32']:
                    num_regs_per_val = 2
                elif data_type in ['INT64', 'UINT64', 'FLOAT64']:
                    num_regs_per_val = 4
                
                if num_regs_per_val > 1:
                    swapped_registers = []
                    for i in range(0, len(registers), num_regs_per_val):
                        chunk = registers[i:i+num_regs_per_val]
                        swapped_registers.extend(chunk[::-1])
                    registers = swapped_registers

            # After manual swapping, we tell the decoder the word order is standard.
            decoder = BinaryPayloadDecoder.fromRegisters(
                registers,
                byteorder=byteorder_map[byte_order],
                wordorder=Endian.BIG 
            )

            if data_type == 'BOOL':
                return [bool(register & (1 << i)) for register in registers for i in range(16)]
            elif data_type == 'BYTE':
                byte_values = []
                for reg in registers:
                    if byte_order == 'big':
                        byte_values.append((reg >> 8) & 0xFF)
                        byte_values.append(reg & 0xFF)
                    else:
                        byte_values.append(reg & 0xFF)
                        byte_values.append((reg >> 8) & 0xFF)
                return byte_values
            elif data_type == 'ASCII':
                char_list = []
                for register in registers:
                    if byte_order == 'big':
                        char_list.append(chr((register >> 8) & 0xFF))
                        char_list.append(chr(register & 0xFF))
                    else:
                        char_list.append(chr(register & 0xFF))
                        char_list.append(chr((register >> 8) & 0xFF))
                return [''.join(char_list).rstrip('\x00')]
            elif data_type == 'INT16':
                return [decoder.decode_16bit_int() for _ in range(len(registers))]
            elif data_type == 'UINT16':
                return [decoder.decode_16bit_uint() for _ in range(len(registers))]
            elif data_type == 'INT32':
                return [decoder.decode_32bit_int() for _ in range(len(registers) // 2)]
            elif data_type == 'UINT32':
                return [decoder.decode_32bit_uint() for _ in range(len(registers) // 2)]
            elif data_type == 'INT64':
                return [decoder.decode_64bit_int() for _ in range(len(registers) // 4)]
            elif data_type == 'UINT64':
                return [decoder.decode_64bit_uint() for _ in range(len(registers) // 4)]
            elif data_type == 'FLOAT32':
                return [decoder.decode_32bit_float() for _ in range(len(registers) // 2)]
            elif data_type == 'FLOAT64':
                return [decoder.decode_64bit_float() for _ in range(len(registers) // 4)]
            elif data_type == 'UNIX_TIMESTAMP':
                if len(registers) >= 2:
                    timestamp = decoder.decode_32bit_uint()
                    try:
                        dt = datetime.fromtimestamp(timestamp)
                        return [dt.strftime('%Y-%m-%d %H:%M:%S')]
                    except (ValueError, OSError):
                        return [f"无效时间戳: {timestamp}"]
                else:
                    return ["时间戳数据不足"]
            else:
                self.logger.warning(f"未知的数据类型: {data_type}，返回原始数据")
                return registers

        except Exception as e:
            self.logger.error(f"处理数据时发生错误: {str(e)}")
            return registers

    def read_holding_registers(self, address, count, slave_id=None, data_type='UINT16', byte_order='big', word_order='big'):
        return self._read_registers(address, count, slave_id, data_type, self.client.read_holding_registers, byte_order, word_order)

    def read_input_registers(self, address, count, slave_id=None, data_type='UINT16', byte_order='big', word_order='big'):
        return self._read_registers(address, count, slave_id, data_type, self.client.read_input_registers, byte_order, word_order)

    def read_coils(self, address, count, slave_id=None):
        return self._read_bits(address, count, slave_id, self.client.read_coils)

    def read_discrete_inputs(self, address, count, slave_id=None):
        return self._read_bits(address, count, slave_id, self.client.read_discrete_inputs)

    def report_slave_id(self, slave_id=None):
        if not self.client:
            return None, "", ""
        try:
            self.last_sent_packet = b''
            self.last_received_packet = b''
            result = self.client.report_slave_id(slave=slave_id or self._slave_id)
            sent = self.format_packet(self.last_sent_packet)
            received_raw = self.last_received_packet

            if isinstance(result, (ModbusIOException, ExceptionResponse)):
                self.logger.error(f"FC11H Modbus error: {result}")
                return None, sent, self.format_packet(received_raw)

            # --- Direct and Final Parsing of Raw Response Bytes ---
            # This method is independent of the pymodbus object structure.
            # Response structure: MBAP(7 bytes) + PDU(variable)
            # PDU: Func Code(1) + Byte Count(1) + Data(N)
            
            if not received_raw or len(received_raw) < 9: # Min length for MBAP + Func Code + Byte Count
                raise ValueError(f"Invalid or empty response packet: {received_raw}")

            pdu = received_raw[7:] # Skip MBAP header
            byte_count = pdu[1]
            
            if len(pdu) - 2 != byte_count:
                raise ValueError(f"Byte count mismatch in PDU. Expected {byte_count}, got {len(pdu) - 2}")

            info_list = []
            
            reported_slave_id = pdu[2]
            run_status_byte = pdu[3]
            vendor_data = pdu[4:]

            info_list.append(f"Function Code: {pdu[0]} (Report Slave ID)")
            info_list.append(f"Byte Count: {byte_count}")
            info_list.append(f"Slave ID (from PDU): {reported_slave_id}")
            info_list.append(f"Run Status: {'ON' if run_status_byte == 0xFF else 'OFF'}")

            # Attempt to find a readable ASCII string within the vendor data
            try:
                import re
                matches = re.findall(b"([ -~]{4,})", vendor_data)
                ascii_parts = [m.decode('ascii') for m in matches]
                if ascii_parts:
                    info_list.append(f"Vendor/Model (ASCII): {', '.join(ascii_parts)}")
            except Exception as e:
                self.logger.warning(f"Could not parse ASCII from vendor info: {e}")

            hex_data = ' '.join(f'{b:02X}' for b in vendor_data)
            info_list.append(f"Vendor Specific Data (Hex): {hex_data}")

            return info_list, sent, self.format_packet(received_raw)
            
        except Exception as e:
            self.logger.error(f"FC11H (report_slave_id) operation failed: {str(e)}")
            return None, self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet)

    def read_write_multiple_registers(self, read_address, read_count, write_address, write_registers, slave_id=None, data_type='UINT16', byte_order='big', word_order='big'):
        if not self.client:
            return None, "", ""
        try:
            self.last_sent_packet = b''
            self.last_received_packet = b''
            # Explicitly name arguments to avoid positional argument confusion
            result = self.client.read_write_multiple_registers(
                read_address=read_address,
                read_count=read_count,
                write_address=write_address,
                write_registers=write_registers,
                slave=slave_id or self._slave_id
            )
            sent = self.format_packet(self.last_sent_packet)
            received = self.format_packet(self.last_received_packet)
            if isinstance(result, (ModbusIOException, ExceptionResponse)):
                return None, sent, received
            
            from data_processor import DataProcessor, ByteOrder, WordOrder
            dp = DataProcessor()
            processed_result = dp.process_data(result.registers, data_type, ByteOrder(byte_order), WordOrder(word_order))
            return processed_result, sent, received
        except Exception as e:
            self.logger.error(f"FC23 (read_write_multiple_registers) 操作时发生错误: {str(e)}")
            return None, self.format_packet(self.last_sent_packet), self.format_packet(self.last_received_packet)
