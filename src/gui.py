##大牛大巨婴

import sys
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QTextEdit, QLabel, QFileDialog, 
                             QTableWidgetItem, QComboBox,QPlainTextEdit,QGridLayout)
from PyQt6.QtCore import Qt, QTimer
from modbus_debugger import ModbusDebugger
from data_processor import DataProcessor
from PyQt6.QtGui import  QPixmap,QFont

class ModbusBabyGUI(QMainWindow):
    def __init__(self, config=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.setWindowTitle("ModbusBaby")
        self.setGeometry(100, 100, 800, 600)

        self.modbus_debugger = None
        self.data_processor = DataProcessor()
        # 添加这一行来初始化 slave_id
        self.slave_id = self.config.get('default_slave_id', 1)
        self.sent_packets = []
        self.received_packets = []
        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self.poll_register)

        self.show_packets = False  # 用于跟踪报文显示区域的状态       
        self.init_ui()
##########################################################################################
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.setMinimumSize(800, 600)  # 设置最小大小
        self.resize(1000, 600)  # 设置初始大小
        # 创建所有UI元素
        self.create_ui_elements()

        # 设置布局
        self.setup_layout()

        self.update_data_type_visibility()

    def create_ui_elements(self):
        # 标题
        self.title_label = QLabel("😄大牛大巨婴👌")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Logo
        self.logo_label = QLabel()
        pixmap = QPixmap("resources/modbuslogo.png")
        scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(scaled_pixmap)
        self.logo_label.setFixedSize(scaled_pixmap.size())
        self.logo_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.logo_label.setStyleSheet("background: transparent;")



        # 连接设置
        self.host_input = QLineEdit(self.config.get('default_host', 'localhost'))
        self.port_input = QLineEdit(str(self.config.get('default_port', 502)))
        self.slave_id_input = QLineEdit(str(self.slave_id))
        self.connect_button = QPushButton("连接")
        self.connect_button.clicked.connect(self.connect_to_device)

        # 操作区域
        self.start_address_input = QLineEdit()
        self.end_address_input = QLineEdit()
        self.value_input = QLineEdit()
        self.register_type_combo = QComboBox()
        self.register_type_combo.addItems(['Holding Register', 'Input Register', 'Discrete Input', 'Coil'])
        self.register_type_combo.currentTextChanged.connect(self.update_data_type_visibility)
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(['INT16', 'UINT16', 'INT32', 'UINT32', 'FLOAT32', 'FLOAT64', 'BOOL'])
        self.read_button = QPushButton("读取")
        self.read_button.clicked.connect(self.read_register)
        self.write_button = QPushButton("写入")
        self.write_button.clicked.connect(self.write_register)
        # 调整输入框的最小宽度
        self.start_address_input.setMinimumWidth(100)
        self.end_address_input.setMinimumWidth(100)
        self.value_input.setMinimumWidth(625)


        # 报文显示区域
        self.sent_packet_display = QPlainTextEdit()
        self.sent_packet_display.setReadOnly(True)
        self.received_packet_display = QPlainTextEdit()
        self.received_packet_display.setReadOnly(True)

        # 日志输出
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # 清空按钮
        self.clear_info_button = QPushButton("清空信息区")
        self.clear_info_button.clicked.connect(self.clear_info)
        self.clear_packet_button = QPushButton("清空报文区")
        self.clear_packet_button.clicked.connect(self.clear_packets)

        # 轮询设置
        self.polling_interval_input = QLineEdit(str(self.config.get('polling_interval', 1000)))
        self.start_polling_button = QPushButton("开始轮询")
        self.start_polling_button.clicked.connect(self.start_polling)
        self.stop_polling_button = QPushButton("停止轮询")
        self.stop_polling_button.clicked.connect(self.stop_polling)
        self.stop_polling_button.setEnabled(False)

    def setup_layout(self):
        # 主布局
        main_layout = QVBoxLayout()
        # 第一行：Logo 和标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.logo_label, 0, Qt.AlignmentFlag.AlignVCenter)
        title_layout.addStretch(1)  # 添加弹性空间
        title_layout.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(title_layout)
        
        # 第二行：连接设置
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("主机:"))
        connection_layout.addWidget(self.host_input)
        connection_layout.addWidget(QLabel("端口:"))
        connection_layout.addWidget(self.port_input)
        connection_layout.addWidget(QLabel("从设备ID:"))
        connection_layout.addWidget(self.slave_id_input)
        connection_layout.addWidget(self.connect_button)
        connection_layout.addStretch(1)
        main_layout.addLayout(connection_layout)    

        # 第三行：操作区域
        operation_layout = QHBoxLayout()
        operation_layout.addWidget(QLabel("起始地址:"))
        operation_layout.addWidget(self.start_address_input)
        operation_layout.addWidget(QLabel("结束地址:"))
        operation_layout.addWidget(self.end_address_input)
        operation_layout.addWidget(self.register_type_combo)
        operation_layout.addWidget(self.data_type_combo)
        operation_layout.addStretch(1)
        main_layout.addLayout(operation_layout)

        # 第四行：读取和写入按钮
        button_layout = QHBoxLayout()
        button_layout.addWidget(QLabel("值:"))
        button_layout.addWidget(self.value_input)
        button_layout.addWidget(self.read_button)
        button_layout.addWidget(self.write_button)
        button_layout.addStretch(1)
        main_layout.addLayout(button_layout)

        # 信息区（日志输出）和清空按钮
        info_layout = QVBoxLayout()
        # 信息区标题和清空按钮
        clear_info_layout = QHBoxLayout()
        clear_info_layout.addWidget(QLabel("信息:"))
        clear_info_layout.addStretch(1)        
        clear_info_layout.addWidget(self.clear_info_button)
        info_layout.addLayout(clear_info_layout)
        # 日志输出
        info_layout.addWidget(self.log_output)
        main_layout.addLayout(info_layout)

        # 报文显示区域
        packet_layout = QGridLayout()

        # 发送的报文区
        packet_layout.addWidget(QLabel("发送的报文:"), 0, 0)
        packet_layout.addWidget(self.sent_packet_display, 1, 0)

        # 接收的报文区
        received_header = QHBoxLayout()
        received_header.addWidget(QLabel("接收的报文:"))
        received_header.addStretch(1)
        received_header.addWidget(self.clear_packet_button)
        
        packet_layout.addLayout(received_header, 0, 1)
        packet_layout.addWidget(self.received_packet_display, 1, 1)

        main_layout.addLayout(packet_layout)

        # 轮询设置
        polling_layout = QHBoxLayout()
        polling_layout.addWidget(QLabel("轮询间隔 (ms):"))
        polling_layout.addWidget(self.polling_interval_input)
        polling_layout.addWidget(self.start_polling_button)
        polling_layout.addWidget(self.stop_polling_button)
        polling_layout.addStretch(1)
        main_layout.addLayout(polling_layout)

        # 设置主布局
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

##########################################################################################


    def connect_to_device(self):
        host = self.host_input.text()
        port = int(self.port_input.text())
        self.slave_id = int(self.slave_id_input.text())
        self.logger.info(f"尝试连接到 {host}:{port}，从设备ID: {self.slave_id}")
        if self.modbus_debugger is None:
            self.modbus_debugger = ModbusDebugger(host, port, self.slave_id)
        if self.modbus_debugger.connect():
            self.log_output.append(f"成功连接到 {host}:{port}，从设备ID: {self.slave_id}")
            # 添加以下调试代码
            print("Debug - 连接成功。尝试进行测试读取。")
            result, sent, received = self.modbus_debugger.read_holding_registers(0, 1, self.slave_id)
            print(f"Debug - 测试读取结果: {result}")
            print(f"Debug - 测试读取发送的报文: {sent}")
            print(f"Debug - 测试读取接收的报文: {received}")
        else:
            self.log_output.append(f"连接失败: {host}:{port}")
            self.log_output.append("请确保 Modbus TCP 服务器正在运行，并检查主机、端口和从设备ID设置")

            # 添加以下调试代码
            print("Debug - 连接失败。无法进行测试读取。")


    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择Modbus地址表文件", "", "All Files (*);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;PDF Files (*.pdf);;Image Files (*.png *.jpg *.jpeg)")
        if file_path:
            self.file_path_input.setText(file_path)

    def parse_file(self):
        file_path = self.file_path_input.text()
        if file_path:
            df = self.document_parser.parse_file(file_path)
            if df is not None:
                self.update_address_table(df)
                self.log_output.append(f"成功解析文件: {file_path}")
            else:
                self.log_output.append(f"解析文件失败: {file_path}")

    def update_address_table(self, df):
        self.address_table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.address_table.setItem(i, 0, QTableWidgetItem(str(row['地址'])))
            self.address_table.setItem(i, 1, QTableWidgetItem(row['描述']))
            self.address_table.setItem(i, 2, QTableWidgetItem(row['数据类型']))
            self.address_table.setItem(i, 3, QTableWidgetItem(row['单位']))


    def toggle_packet_display(self):
        self.show_packets = not self.show_packets
        if self.show_packets:
            self.packet_display.show()
            self.toggle_packet_button.setText("隐藏报文")
        else:
            self.packet_display.hide()
            self.toggle_packet_button.setText("显示报文")

    def clear_packets(self):
        self.sent_packets.clear()
        self.received_packets.clear()

    def copy_packets(self):
        clipboard = QApplication.clipboard()
        text = f"发送的报文:\n{self.sent_packets.toPlainText()}\n\n接收的报文:\n{self.received_packets.toPlainText()}"
        clipboard.setText(text)

    def read_register(self):
        if self.modbus_debugger:
            start_address = int(self.start_address_input.text())
            end_address = int(self.end_address_input.text())
            register_type = self.register_type_combo.currentText()
            data_type = self.data_type_combo.currentText()

            count = end_address - start_address + 1
            # 根据数据类型调整读取的寄存器数量
            registers_per_value = 1
            if data_type in ['INT32', 'UINT32', 'FLOAT32']:
                registers_per_value = 2
            elif data_type == 'FLOAT64':
                registers_per_value = 4

            # 确保读取的寄存器数量是正确的倍数
            count = max(count, registers_per_value)
            if count % registers_per_value != 0:
                count = (count // registers_per_value + 1) * registers_per_value
            
            self.logger.debug(f"尝试读取 - 类型: {register_type}, 起始地址: {start_address}, 数量: {count}, 数据类型: {data_type}")

            try:
                if register_type == 'Holding Register':
                    result, sent_packet, received_packet = self.modbus_debugger.read_holding_registers(start_address, count, self.slave_id, data_type)
                elif register_type == 'Input Register':
                    result, sent_packet, received_packet = self.modbus_debugger.read_input_registers(start_address, count, self.slave_id, data_type)
                elif register_type == 'Discrete Input':
                    result, sent_packet, received_packet = self.modbus_debugger.read_discrete_inputs(start_address, count, self.slave_id)
                elif register_type == 'Coil':
                    result, sent_packet, received_packet = self.modbus_debugger.read_coils(start_address, count, self.slave_id)
                else:
                    self.logger.error(f"不支持的寄存器类型: {register_type}")
                    return

                self.sent_packets.append(sent_packet)
                self.received_packets.append(received_packet)

                if result is not None:
                    self.logger.debug(f"读取成功 - 结果: {result}")
                    if register_type in ['Discrete Input', 'Coil']:
                        formatted_result = self.format_result(result, 'BOOL')
                    else:
                        formatted_result = self.format_result(result, data_type)
                    self.value_input.setText(formatted_result)
                    self.log_output.append(f"读取 {register_type} {start_address}-{end_address}: {formatted_result}")
                else:
                    self.logger.error(f"读取 {register_type} {start_address}-{end_address} 失败")
                    self.log_output.append(f"读取 {register_type} {start_address}-{end_address} 失败")
                self.update_packet_display()
            except Exception as e:
                self.logger.error(f"读取操作发生错误: {str(e)}")
                self.log_output.append(f"读取操作发生错误: {str(e)}")     
        else:
            self.logger.error("Modbus 调试器未初始化")
            self.log_output.append("Modbus 调试器未初始化")

    def write_register(self):
        if not self.modbus_debugger or not self.modbus_debugger.client:
            self.log_output.append("错误：Modbus 客户端未连接")
            return

        start_address = int(self.start_address_input.text())
        end_address = int(self.end_address_input.text())
        register_type = self.register_type_combo.currentText()
        data_type = self.data_type_combo.currentText()
        value = self.value_input.text()

        try:
            count = end_address - start_address + 1            
            # 根据数据类型处理输入值
            if register_type == 'Coil':
                values = [bool(int(v.strip())) for v in value.split(',')]
                modbus_type = 'coil'
                data_type = 'BOOL'  # 添加：强制将 Coil 的数据类型设置为 BOOL
            elif register_type == 'Holding Register':
                if data_type in ['FLOAT32', 'FLOAT64']:
                    values = [float(v.strip()) for v in value.split(',')]
                elif data_type in ['INT16','INT32']:
                    values = [int(v.strip()) for v in value.split(',')]
                elif data_type in ['UINT16', 'UINT32']:  # 修改：单独处理 UINT 类型
                    values = []
                    for v in value.split(','):
                        int_value = int(v.strip())
                        if int_value < 0:
                            raise ValueError(f"UINT 类型不能写入负数: {int_value}")
                        values.append(int_value)
                elif data_type == 'BOOL':
                    values = [bool(int(v.strip())) for v in value.split(',')]
                else:
                    self.log_output.append(f"错误：不支持的数据类型 {data_type}")
                    return
                modbus_type = 'holding'
            elif register_type in ['Input Register', 'Discrete Input'] :
                self.log_output.append(f"错误：{register_type} 不支持写操作")
                return
            else:
                self.log_output.append(f"错误：未知的寄存器类型 {register_type}")
                return
       
            # 检查数据类型和地址范围是否匹配
            registers_per_value = 1
            if data_type in ['INT32', 'UINT32', 'FLOAT32']:
                registers_per_value = 2
            elif data_type == 'FLOAT64':
                registers_per_value = 4

            if count % registers_per_value != 0:
                self.log_output.append(f"错误：地址范围 ({count}) 不是 {data_type} 类型所需寄存器数 ({registers_per_value}) 的整数倍")
                return

            if len(values) * registers_per_value != count:
                self.log_output.append(f"错误：输入值的数量 ({len(values)}) 与地址范围 ({count}) 不匹配")
                return
            
            # 添加：检查 UINT 类型的值是否在有效范围内
            if data_type == 'UINT16':
                for v in values:
                    if v > 65535:
                        raise ValueError(f"UINT16 值超出范围 (0-65535): {v}")
            elif data_type == 'UINT32':
                for v in values:
                    if v > 4294967295:
                        raise ValueError(f"UINT32 值超出范围 (0-4294967295): {v}")
           
            success, message, result = self.modbus_debugger.write_registers(start_address, values, self.slave_id, data_type)
 
            # 修改：根据寄存器类型选择不同的写入方法
            if register_type == 'Coil':
                success, message, result = self.modbus_debugger.write_coils(start_address, values, self.slave_id)
            else:  # Holding Register
                success, message, result = self.modbus_debugger.write_registers(start_address, values, self.slave_id, data_type)

            if success:
                self.log_output.append(f"成功写入 {register_type} {start_address}-{end_address}: {value}")
            else:
                self.log_output.append(f"写入失败: {message}")
            
           
            # 更新报文显示
            if hasattr(result, 'sent_packet') and hasattr(result, 'received_packet'):
                self.sent_packets.append(result.sent_packet)
                self.received_packets.append(result.received_packet)
                self.update_packet_display()

        except ValueError as e:
            self.log_output.append(f"错误：输入值无效 - {str(e)}")
        except Exception as e:
            self.log_output.append(f"写入操作发生错误: {str(e)}")

    def update_data_type_visibility(self):
        register_type = self.register_type_combo.currentText()
        if register_type in ['Discrete Input', 'Coil']:
            self.data_type_combo.setCurrentText('BOOL')
            self.data_type_combo.setEnabled(False)
        else:
            self.data_type_combo.setEnabled(True)

    def start_polling(self):
        interval = int(self.polling_interval_input.text())
        self.polling_timer.start(interval)
        self.start_polling_button.setEnabled(False)
        self.stop_polling_button.setEnabled(True)
        self.log_output.append("开始轮询")

    def stop_polling(self):
        self.polling_timer.stop()
        self.start_polling_button.setEnabled(True)
        self.stop_polling_button.setEnabled(False)
        self.log_output.append("停止轮询")

    def poll_register(self):
        if self.modbus_debugger:
            start_address = int(self.start_address_input.text())
            end_address = int(self.end_address_input.text())
            register_type = self.register_type_combo.currentText()
            data_type = self.data_type_combo.currentText()

            count = end_address - start_address + 1

            # 根据数据类型调整读取的寄存器数量
            registers_per_value = 1
            if data_type in ['INT32', 'UINT32', 'FLOAT32']:
                registers_per_value = 2
            elif data_type == 'FLOAT64':
                registers_per_value = 4

            # 确保读取的寄存器数量是正确的倍数
            count = max(count, registers_per_value)
            if count % registers_per_value != 0:
                count = (count // registers_per_value + 1) * registers_per_value

            if register_type == 'Holding Register':
                result, sent_packet, received_packet = self.modbus_debugger.read_holding_registers(start_address, count, self.slave_id)
            elif register_type == 'Input Register':
                result, sent_packet, received_packet = self.modbus_debugger.read_input_registers(start_address, count, self.slave_id)
            elif register_type == 'Discrete Input':
                result, sent_packet, received_packet = self.modbus_debugger.read_discrete_inputs(start_address, count, self.slave_id)
            elif register_type == 'Coil':
                result, sent_packet, received_packet = self.modbus_debugger.read_coils(start_address, count, self.slave_id)

            self.sent_packets.append(sent_packet)
            self.received_packets.append(received_packet)

            if result is not None:
                if register_type in ['Holding Register', 'Input Register']:
                    processed_values = []
                    for i in range(0, len(result), registers_per_value):
                        value = self.modbus_debugger.process_data(result[i:i+registers_per_value], data_type)
                        # 如果 process_data 返回的是列表，我们只取第一个元素
                        processed_values.append(value[0] if isinstance(value, list) else value)
                else:
                    processed_values = result

                # 将处理后的值转换为字符串
                values_str = ', '.join(map(str, processed_values))
                self.value_input.setText(values_str)
                self.log_output.append(f"轮询 {register_type} {start_address}-{end_address}: {values_str}")
            else:
                self.log_output.append(f"轮询 {register_type} {start_address}-{end_address} 失败")
            self.update_packet_display()

    def format_result(self, result, data_type):

        if data_type == 'BOOL':
            return ', '.join('1' if bit else '0' for bit in result)
        elif data_type in ['INT16', 'UINT16', 'INT32', 'UINT32']:
            return ', '.join(map(str, result))
        elif data_type in ['FLOAT32', 'FLOAT64']:
            return ', '.join(f"{x:.6f}" for x in result)
        else:
            return str(result)


    def update_packet_display(self):
        sent_text = "\n".join(self.sent_packets[-10:])  # 只显示最近的10条
        received_text = "\n".join(self.received_packets[-10:])  # 只显示最近的10条
        print(f"Debug - Sent packets: {self.sent_packets}")  # 调试输出
        print(f"Debug - Received packets: {self.received_packets}")  # 调试输出
        
        if not sent_text and not received_text:
            print("Debug - No packets to display")
            return

        self.sent_packet_display.setPlainText(f"发送：\n{sent_text}")
        self.received_packet_display.setPlainText(f"接收：\n{received_text}")
        
        print(f"Debug - Sent text set to: {sent_text}")
        print(f"Debug - Received text set to: {received_text}")

        # 强制更新显示
        self.sent_packet_display.update()
        self.received_packet_display.update()

    def read_registers_in_chunks(self, address, count, slave_id=None, register_type='holding', max_count=125):
        results = []
        sent_packets = []
        received_packets = []
        for i in range(0, count, max_count):
            chunk_count = min(max_count, count - i)
            self.log_capture.seek(0)
            self.log_capture.truncate()
            
            if register_type == 'holding':
                result = self.client.read_holding_registers(address + i, chunk_count, slave=slave_id or self.slave_id)
            elif register_type == 'input':
                result = self.client.read_input_registers(address + i, chunk_count, slave=slave_id or self.slave_id)
            elif register_type == 'coil':
                result = self.client.read_coils(address + i, chunk_count, slave=slave_id or self.slave_id)
            elif register_type == 'discrete':
                result = self.client.read_discrete_inputs(address + i, chunk_count, slave=slave_id or self.slave_id)
            else:
                self.logger.error(f"不支持的寄存器类型: {register_type}")
                return None, "", ""
            
            log_content = self.log_capture.getvalue()
            sent_packet, received_packet = self.extract_packets_from_log(log_content)
            sent_packets.append(sent_packet)
            received_packets.append(received_packet)
            
            if isinstance(result, ModbusIOException):
                self.logger.error(f"读取失败: {result}")
                return None, "\n".join(sent_packets), "\n".join(received_packets)
            
            if register_type in ['holding', 'input']:
                results.extend(result.registers)
            else:
                results.extend(result.bits)
        
        return results, "\n".join(sent_packets), "\n".join(received_packets)
    # 新增：清空信息区方法
    def clear_info(self):
        self.log_output.clear()

    # 新增：清空报文区方法
    def clear_packets(self):
        self.sent_packet_display.clear()
        self.received_packet_display.clear()
        self.sent_packets.clear()
        self.received_packets.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModbusBabyGUI()
    window.show()
    sys.exit(app.exec())