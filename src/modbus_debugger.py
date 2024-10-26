#大牛大巨婴
import logging
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusIOException,ModbusException
from pymodbus.pdu import ExceptionResponse
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.constants import Endian
import serial,serial.tools.list_ports 
import os
import io

class ModbusDebugger:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.client = None
        self.log_capture = io.StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        self.log_handler.setLevel(logging.DEBUG)

        pymodbus_logger = logging.getLogger('pymodbus')
        pymodbus_logger.setLevel(logging.DEBUG)
        pymodbus_logger.addHandler(self.log_handler)

    def get_available_serial_ports(self):
        try:
            # Using pyserial's tools
            pyserial_ports = serial.tools.list_ports.comports()
            existing_ports =[]
            if pyserial_ports:
                for port in pyserial_ports:
                    existing_ports.append(port.device)
            manual_ports = [f'/dev/ttyS{i}' for i in range(10)] 
            for port in manual_ports:
                if os.path.exists(port):
                    existing_ports.append(port)
            return existing_ports
        except ImportError:
            self.logger.warning("pyserial 库未安装，无法获取可用串口列表")
            return []
        except Exception as e:
            self.logger.error(f"获取串口列表时发生错误: {str(e)}")
            return []

    def connect_tcp(self, host, port, slave_id):
        try:
            self.client = ModbusTcpClient(host=host, port=port)
            self.slave_id = slave_id
            return self.client.connect()
        except Exception as e:
            self.logger.error(f"TCP 连接失败: {str(e)}")
            return False

    def connect_rtu(self, port, baud_rate, data_bits, stop_bits, parity, slave_id):
        try:
            self.client = ModbusSerialClient(
                port = port,
                baudrate = baud_rate,
                bytesize = data_bits,
                parity=parity[0].upper(),
                stopbits=stop_bits
            )
            self.slave_id = slave_id
            return self.client.connect()
        except Exception as e:
            self.logger.error(f"RTU 连接失败: {str(e)}")
            return False
        
    def connect_rtu_over_tcp(self, host, port, slave_id):
        try:
            self.client = ModbusTcpClient(
                host =host, 
                port = port,
                frame = ModbusRtuFramer,
                timeout = 3,
                retries = 1
            )
            self.slave_id = slave_id
            return self.client.connect()
        except Exception as e:
            self.logger.error(f"RTU over TCP connect failed: {str(e)}")
            return False

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None
            return True
        return False

    def connect(self):
        try:
            if self.config['connection_type'] == 'TCP':
                return self.connect_tcp(
                    self.config['tcp']['ip'],
                    self.config['tcp']['port'],
                    self.config['tcp']['slave_id']
                )
            elif self.config['connection_type'] == 'RTU':
                return self.connect_rtu(
                    self.config['rtu']['serial_port'],
                    self.config['rtu']['baud_rate'],
                    self.config['rtu']['data_bits'],
                    self.config['rtu']['stop_bits'],
                    self.config['rtu']['parity'],
                    self.config['rtu']['slave_id']
                )
            elif self.config['connection_type'] == 'RTU_OVER_TCP':
                return self.connect_rtu_over_tcp(
                    self.config['rtu_over_tcp']['ip'],
                    self.config['rtu_over_tcp']['port'],
                    self.config['rtu_over_tcp']['slave_id']
                )
            else:
                raise ValueError(f"不支持的连接类型: {self.config['connection_type']}")
        except Exception as e:
            self.logger.error(f"连接时发生错误: {str(e)}")
            return False

    def disconnect(self):
        if self.client:
            self.client.close()
            self.logger.info("已断开连接")


    def write_float(self, address, value, data_type='FLOAT32', byte_order='big', word_order='big'):
        # 在需要使用 Endian 的地方
        byteorder = Endian.BIG if byte_order == 'big' else Endian.LITTLE
        wordorder = Endian.BIG if word_order == 'big' else Endian.LITTLE

        builder = BinaryPayloadBuilder(byteorder=byteorder, wordorder=wordorder)
        if data_type == 'FLOAT32':
            builder.add_32bit_float(value)
        elif data_type == 'FLOAT64':
            builder.add_64bit_float(value)
        
        registers = builder.to_registers()
        return self.client.write_registers(address, registers)

    def read_float(self, address, count, data_type='FLOAT32', byte_order='big', word_order='big'):
        # 在需要使用 Endian 的地方
        byteorder = Endian.BIG if byte_order == 'big' else Endian.LITTLE
        wordorder = Endian.BIG if word_order == 'big' else Endian.LITTLE
        
        response = self.client.read_holding_registers(address, count)
        decoder = BinaryPayloadDecoder.fromRegisters(response.registers, byteorder=byteorder, wordorder=wordorder)
           
        if data_type == 'FLOAT32':
            return decoder.decode_32bit_float()
        elif data_type == 'FLOAT64':
            return decoder.decode_64bit_float()



    def write_coil(self, address, value, slave_id=None):
        if not self.client:
            self.logger.error("未连接到设备")
            return False, "", ""
        try:
            self.log_capture.seek(0)
            self.log_capture.truncate()
            
            self.logger.debug(f"尝试写入单个线圈 - 地址: {address}, 值: {value}, 从设备ID: {slave_id or self.slave_id}")
            
            result = self.client.write_coil(address, value, slave=slave_id or self.slave_id)
            
            log_content = self.log_capture.getvalue()
            sent_packet, received_packet = self.extract_packets_from_log(log_content)
            
            if isinstance(result, ModbusIOException):
                self.logger.error(f"写入线圈失败: {result}")
                return False, sent_packet, received_packet
            
            self.logger.debug(f"成功写入线圈: {result}")
            
            return True, sent_packet, received_packet
        except Exception as e:
            self.logger.error(f"写入线圈时发生错误: {str(e)}")
            return False, "", ""

    def write_coils(self, address, values, slave_id=None):
        if not self.client:
            self.logger.error("未连接到设备")
            return False, "", ""
        try:
            self.log_capture.seek(0)
            self.log_capture.truncate()
            
            self.logger.debug(f"尝试写入多个线圈 - 起始地址: {address}, 值: {values}, 从设备ID: {slave_id or self.slave_id}")
            
            result = self.client.write_coils(address, values, slave=slave_id or self.slave_id)
            
            log_content = self.log_capture.getvalue()
            sent_packet, received_packet = self.extract_packets_from_log(log_content)
            
            if isinstance(result, ModbusIOException):
                self.logger.error(f"写入多个线圈失败: {result}")
                return False, sent_packet, received_packet
            
            self.logger.debug(f"成功写入多个线圈: {result}")
            
            return True, sent_packet, received_packet
        except Exception as e:
            self.logger.error(f"写入多个线圈时发生错误: {str(e)}")
            return False, "", ""
        
    def write_register(self, address, values, slave_id=None, register_type='holding'):
        if not self.client.is_socket_open():
            return False, "客户端未连接", ""

        try:
            if register_type == 'holding':
                if len(values) == 1:
                    result = self.client.write_register(address, values[0], slave=slave_id or self.slave_id)
                else:
                    result = self.client.write_registers(address, values, slave=slave_id or self.slave_id)
            elif register_type == 'coil':
                if len(values) == 1:
                    result = self.client.write_coil(address, bool(values[0]), slave=slave_id or self.slave_id)
                else:
                    result = self.client.write_coils(address, [bool(v) for v in values], slave=slave_id or self.slave_id)
            else:
                return False, f"不支持的寄存器类型: {register_type}", ""

            if isinstance(result, ModbusIOException):
                return False, str(result), ""
            return True, "写入成功", str(result)
        except Exception as e:
            return False, f"写入时发生错误: {str(e)}", ""


    def write_registers(self, address, values, slave_id=None, data_type='UINT16', byte_order='big', word_order='big'):
        if not self.client:
            self.logger.error("未连接到设备")
            return False, "", ""
        try:
            self.log_capture.seek(0)
            self.log_capture.truncate()
            
            self.logger.debug(f"尝试写入 - 地址: {address}, 值: {values}, 数据类型: {data_type}, 字节序: {byte_order}, 字序: {word_order}")
            
            # 确保 values 是一个列表
            if not isinstance(values, list):
                values = [values]
            # 设置字节序和字序
            # 在需要使用 Endian 的地方
            byteorder = Endian.BIG if byte_order == 'big' else Endian.LITTLE
            wordorder = Endian.BIG if word_order == 'big' else Endian.LITTLE
            
            # 根据数据类型构建正确的寄存器值
            builder = BinaryPayloadBuilder(byteorder=byteorder, wordorder=wordorder)
            if data_type == 'BYTE':
                for value in values:
                    builder.add_8bit_uint(int(value))
            elif data_type == 'FLOAT32':
                for value in values:
                    builder.add_32bit_float(float(value))
            elif data_type == 'FLOAT64':
                for value in values:
                    builder.add_64bit_float(float(value))
            elif data_type in ['INT16', 'UINT16']:
                for value in values:
                    builder.add_16bit_int(int(value))
            elif data_type in ['INT32', 'UINT32']:
                for value in values:
                    builder.add_32bit_int(int(value))
            elif data_type in ['INT64', 'UINT64']:
                for value in values:
                    builder.add_64bit_int(int(value))
            else:
                self.logger.error(f"不支持的数据类型: {data_type}")
                return False, "", ""
            
            registers = builder.to_registers()
            self.logger.debug(f"{data_type} 寄存器值: {registers}")
            
            result = self.client.write_registers(address, registers, slave=slave_id or self.slave_id)
            
            log_content = self.log_capture.getvalue()
            sent_packet, received_packet = self.extract_packets_from_log(log_content)
            
            sent_packet = self.format_packet(sent_packet)
            received_packet = self.format_packet(received_packet)
 

            if isinstance(result, ExceptionResponse):
                self.logger.error(f"写入寄存器失败: {result}")
                #return False, sent_packet, received_packet
                return False, str(result), (sent_packet, received_packet)
            self.logger.debug(f"写入成功 - 结果: {result}")
            self.logger.debug(f"提取的报文 - 发送: {sent_packet}, 接收: {received_packet}")  # 添加这行来记录提取的报文
            return True, "写入成功", (sent_packet, received_packet)
        except ModbusException as e:
            self.logger.error(f"写入寄存器时发生Modbus错误: {str(e)}")
            return False, "", ""
        except ValueError as e:
            self.logger.error(f"写入寄存器时发生值错误: {str(e)}")
            return False, "", ""
        except Exception as e:
            self.logger.error(f"写入寄存器时发生未知错误: {str(e)}")
            return False, "", ""

    def _read_registers(self, address, count, slave_id, data_type,read_func):
        if not self.client:
            self.logger.error("未连接到设备")
            return None, "", ""
        try:
            self.log_capture.seek(0)
            self.log_capture.truncate()
            self.logger.debug(f"尝试读取寄存器 - 地址: {address}, 数量: {count}, 从设备ID: {slave_id or self.slave_id}, 数据类型: {data_type}")
            result = getattr(self.client, function)(address, count, slave=slave_id or self.slave_id)
            log_content = self.log_capture.getvalue()
            sent_packet, received_packet = self.extract_packets_from_log(log_content)
            

            if isinstance(result, ExceptionResponse):
                self.logger.error(f"读取寄存器失败: {result}")
                return None, sent_packet, received_packet
            
            self.logger.debug(f"成功读取寄存器: {result.registers}")
            processed_result = self.process_data(result.registers, data_type)
            self.logger.debug(f"处理后的结果: {processed_result}")
            

            return processed_result, sent_packet, received_packet
         
        except ModbusException as e:
            self.logger.error(f"读取寄存器时发生Modbus错误: {str(e)}")
            return None, "", ""
        except Exception as e:
            self.logger.error(f"读取寄存器时发生未知错误: {str(e)}")
            return None, "", ""

    def _read_bits(self, address, count, slave_id, read_func):
        if not self.client:
            self.logger.error("未连接到设备")
            return None, "", ""
        try:
            self.log_capture.seek(0)
            self.log_capture.truncate()
            
            self.logger.debug(f"尝试读取位 - 地址: {address}, 数量: {count}, 从设备ID: {slave_id or self.slave_id}")
            
            result = read_func(address, count, slave=slave_id or self.slave_id)
            
            log_content = self.log_capture.getvalue()
            sent_packet, received_packet = self.extract_packets_from_log(log_content)
            
            if isinstance(result, ExceptionResponse):
                self.logger.error(f"读取位失败: {result}")
                return None, sent_packet, received_packet
            
            self.logger.debug(f"成功读取位: {result.bits}")
            
            return result.bits, sent_packet, received_packet
        except ModbusException as e:
            self.logger.error(f"读取位时发生 Modbus 错误: {str(e)}")
            return None, "", ""
        except Exception as e:
            self.logger.error(f"读取位时发生未知错误: {str(e)}")
            return None, "", ""


    def extract_packets_from_log(self, log_content):
        sent_packet = ""
        received_packet = ""
        #print(f"Debug - Extracting packets from log: {log_content}")  # 添加这行
        #for line in log_content.split('\n'):
        #    if "SEND:" in line:
        #        sent_packet = line.split("SEND:")[1].strip()
        #    elif "RECV:" in line:
        #        received_packet = line.split("RECV:")[1].strip()
        
        #print(f"Debug - Raw sent packet: {sent_packet}")
        #print(f"Debug - Raw received packet: {received_packet}")

       
        # 将报文转换为十六进制格式
        #sent_packet = ' '.join([f'{int(x, 16):02X}' for x in sent_packet.split()])
        #received_packet = ' '.join([f'{int(x, 16):02X}' for x in received_packet.split()])
      # 使用正则表达式提取发送和接收的报文
        lines = log_content.split('\n')
        for line in lines:
            if "SEND:" in line:
                sent_packet = line.split("SEND:")[1].strip()
            elif "RECV:" in line:
                received_packet = line.split("RECV:")[1].strip()
        
        self.logger.debug(f"提取的报文 - 发送: {sent_packet}, 接收: {received_packet}")
        return sent_packet, received_packet
        

    def format_packet(self, packet):
        # 移除 "0x" 前缀，将单个 "0" 替换为 "00"
        formatted = ' '.join([f"{int(b, 16):02X}" for b in packet.split()])
        return formatted

    def format_request(self, slave_id, function_code, address, data):
        return f"Slave ID: {slave_id}, Function: {function_code}, Address: {address}, Data: {data}"

    def format_response(self, response):
        if hasattr(response, 'registers'):
            return f"Function: {response.function_code}, Values: {response.registers}"
        elif hasattr(response, 'value'):
            return f"Function: {response.function_code}, Address: {response.address}, Value: {response.value}"
        elif isinstance(response, ExceptionResponse):
            return f"Exception: Function {response.function_code}, Code: {response.exception_code}"
        else:
            return str(response)

    def process_data(self, registers, data_type, byte_order='big', word_order='big'):
       # 方法实现
        try:
            # 在需要使用 Endian 的地方
            byteorder = Endian.BIG if byte_order == 'big' else Endian.LITTLE
            wordorder = Endian.BIG if word_order == 'big' else Endian.LITTLE
            
            decoder = BinaryPayloadDecoder.fromRegisters(
                registers,
                byteorder=byteorder,
                wordorder=wordorder
            )
            
            if data_type == 'BOOL':
                #return [decoder.decode_bits() for _ in range(len(registers) * 16)]
                return [bool(register & (1 << i)) for register in registers for i in range(16)]
                #return [bit for register in registers for bit in decoder.decode_bits()]
            elif data_type == 'BYTE':
                return [decoder.decode_8bit_uint() for _ in range(len(registers) * 2)]
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
            else:
                self.logger.warning(f"未知的数据类型: {data_type}，返回原始数据")
                return registers
        except Exception as e:
            self.logger.error(f"处理数据时发生错误: {str(e)}")
            return registers  # 出错时返回原始寄存器值
        

    def read_registers_in_chunks(self, address, count, slave_id=None, register_type='holding'):
        slave_id = slave_id or self.slave_id
        results = []
        sent_packets = []
        received_packets = []
        
        if register_type in ['holding', 'input']:
            max_count = 123  # 单次读取的最大数量
        elif register_type in ['coil', 'discrete']:
            max_count = 2000
        else:
            self.logger.error(f"不支持的寄存器类型: {register_type}")
            return None, "", ""

        for i in range(0, count, max_count):
            chunk_count = min(max_count, count - i)
            self.log_capture.seek(0)
            self.log_capture.truncate()
            
            try:
                if register_type == 'holding':
                    result = self.client.read_holding_registers(address + i, chunk_count, slave=slave_id or self.slave_id)
                elif register_type == 'input':
                    result = self.client.read_input_registers(address + i, chunk_count, slave=slave_id or self.slave_id)
                elif register_type == 'coil':
                    result = self.client.read_coils(address + i, chunk_count, slave=slave_id or self.slave_id)
                elif register_type == 'discrete':
                    result = self.client.read_discrete_inputs(address + i, chunk_count, slave=slave_id or self.slave_id)
                
                log_content = self.log_capture.getvalue()
                sent_packet, received_packet = self.extract_packets_from_log(log_content)
                sent_packets.append(sent_packet)
                received_packets.append(received_packet)
                
                if isinstance(result, ModbusIOException):
                    raise ModbusIOException(f"读取失败: {result}")
                
                if register_type in ['holding', 'input']:
                    results.extend(result.registers)
                else:  # 对于线圈和离散输入
                    results.extend(result.bits)
            
            except ModbusIOException as e:
                self.logger.error(str(e))
                return None, "\n".join(sent_packets), "\n".join(received_packets)
            except Exception as e:
                self.logger.error(f"读取时发生未知错误: {str(e)}")
                return None, "\n".join(sent_packets), "\n".join(received_packets)
        
        return results, "\n".join(sent_packets), "\n".join(received_packets)

    def read_holding_registers(self, address, count, slave_id=None, data_type='UINT16', byte_order='big', word_order='big'):
        results, sent_packet, received_packet = self.read_registers_in_chunks(address, count, slave_id, 'holding')
        return self.process_data(results, data_type, byte_order, word_order) if results is not None else None, sent_packet, received_packet

    def read_input_registers(self, address, count, slave_id=None, data_type='UINT16', byte_order='big', word_order='big'):
        results, sent_packet, received_packet = self.read_registers_in_chunks(address, count, slave_id, 'input')
        return self.process_data(results, data_type, byte_order, word_order) if results is not None else None, sent_packet, received_packet

    def read_coils(self, address, count, slave_id=None):
        return self.read_registers_in_chunks(address, count, slave_id, 'coil')

    def read_discrete_inputs(self, address, count, slave_id=None):
        return self.read_registers_in_chunks(address, count, slave_id, 'discrete')
