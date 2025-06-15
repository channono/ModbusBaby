##大牛大巨婴
import os
import sys
import logging
import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTextEdit, QLabel, QSplitter,QGroupBox,
                             QTableWidgetItem, QSizePolicy,QStackedWidget, QComboBox)
from PyQt6.QtCore import Qt, QEvent,QSettings,QTimer
from modbus_debugger import ModbusDebugger
from data_processor import DataProcessor
from pymodbus.exceptions import ModbusIOException
from PyQt6.QtGui import  QIcon,QPixmap,QFont, QIntValidator,QColor, QTextCharFormat,QPalette
from utils import resource_path as get_resource_path # Use centralized resource_path

class ModbusBabyGUI(QMainWindow):
    def __init__(self, config=None):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyleSheetTarget, True)
        self.logger = logging.getLogger(__name__)
        self.config = config if config is not None else {}
        self.logger.info(f"初始化 ModbusBabyGUI，配置: {self.config}")
        self.is_connected = False  # 添加一个标志来跟踪连接状态
        try:
            self.logger.info("尝试创建 ModbusDebugger 实例")
            self.modbus_debugger = ModbusDebugger(self.config)
            self.logger.info("ModbusDebugger 实例创建成功")
        except Exception as e:
            self.logger.error(f"创建 ModbusDebugger 实例时出错: {str(e)}")
            self.modbus_debugger = None

        self.setWindowTitle("ModbusBaby - by Daniel BigGiantBaby")
        self.setGeometry(100, 100, 866, 600)
        self.set_window_icon()
        self.create_ui_elements() # Create UI elements once
        self.restore_window_state()


        self.byte_order = 'big'
        self.word_order = 'big'
        self.data_processor = DataProcessor()
        self.slave_id = self.config.get('default_slave_id', 1)
        self.sent_packets = []
        self.received_packets = []
        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self.poll_register)
        self.show_packets = False
        self.init_ui()

    def set_window_icon(self):
        try:
            icon_path = get_resource_path('resources/modbusbaby.ico')
            self.setWindowIcon(QIcon(icon_path))
            self.logger.info(f"Window icon set successfully: {icon_path}")
        except Exception as e:
            self.logger.exception("Error setting window icon")

    def init_ui(self):
        # self.create_ui_elements() # Already called in __init__
        self.setup_validators()
        self.connect_button.clicked.disconnect()  # 断开所有之前的连接
        self.connect_button.clicked.connect(self.toggle_connection)
        buttons = [self.connect_button, self.read_button, self.write_button,
               self.start_polling_button, self.stop_polling_button]
        for button in buttons:
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button.setMinimumSize(80, 32)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Title row
        self.add_title_row(main_layout)
        #2 Setting area
        self.add_settings_area(main_layout)

        # 3. Display area
        display_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter = self.add_display_area(display_splitter)
        main_layout.addWidget(main_splitter, 1)  # 1 是拉伸因子
        # 4. Polling settings
        self.add_polling_settings(main_layout)

    def setup_validators(self):
        # 为从站地址添加验证器
        slave_validator = QIntValidator(0, 247, self)
        self.slave_id_tcp.setValidator(slave_validator)
        self.slave_id_rtu.setValidator(slave_validator)

    def add_title_row(self, parent_layout):
        title_layout = QHBoxLayout()
        # Logo
        logo_path = get_resource_path('resources/modbuslogo.png')
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(150, 50, Qt.AspectRatioMode.KeepAspectRatio))
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # 垂直居中对齐
        title_layout.addWidget(self.logo_label)

        title_layout.addStretch(1)

        # Author title
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # 垂直居中对齐
        title_layout.addWidget(self.title_label)

        parent_layout.addLayout(title_layout)

    def add_settings_area(self, parent_layout):
        settings_group = QGroupBox("")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(5)
        settings_layout.setContentsMargins(5, 5, 5, 5)

        # 1. Connection settings
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("连接类型:"))
        connection_layout.addWidget(self.connection_type)
        connection_layout.addStretch(1)
        connection_layout.addWidget(self.connect_button)
        settings_layout.addLayout(connection_layout)
        # 2. Settings stack (TCP/RTU 设置)
        stack_layout = QHBoxLayout()
        stack_layout.addWidget(self.settings_stack)
        settings_layout.addLayout(stack_layout)

        settings_layout.addWidget(self.settings_stack)

        # 3. 寄存器操作部分
        register_layout = QHBoxLayout()
        register_layout.addWidget(QLabel("起始地址:"))
        register_layout.addWidget(self.start_address_input)
        register_layout.addWidget(QLabel("结束地址:"))
        register_layout.addWidget(self.end_address_input)
        register_layout.addWidget(QLabel("寄存器类型:"))
        register_layout.addWidget(self.register_type_combo)
        register_layout.addWidget(QLabel("数据类型:"))
        register_layout.addWidget(self.data_type_combo)
        register_layout.addWidget(QLabel("字节序:"))
        register_layout.addWidget(self.byte_order_combo)
        register_layout.addWidget(QLabel("字序:"))
        register_layout.addWidget(self.word_order_combo)
        register_layout.addStretch(1)
        register_layout.addWidget(self.read_button)
        settings_layout.addLayout(register_layout)

        # 4. 值输入和读写按钮
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("数值:"))
        value_layout.addWidget(self.value_input)
        value_layout.addWidget(self.write_button)
        settings_layout.addLayout(value_layout)

        # 确保设置区域不会过度扩展
        settings_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        parent_layout.addWidget(settings_group)

        # 创建并设置 TCP 和 RTU 设置页面
        self.create_tcp_settings_page()
        self.create_rtu_settings_page()
    def create_tcp_settings_page(self):
        tcp_widget = QWidget()
        tcp_layout = QHBoxLayout(tcp_widget)
        tcp_layout.addSpacing(10)
        tcp_layout.addWidget(QLabel("IP 地址:"))
        default_ip = self.config.get('tcp', {}).get('ip') if self.config else 'localhost'
        self.ip_address = QLineEdit(default_ip)
        self.ip_address.setFixedWidth(400)
        tcp_layout.addWidget(self.ip_address)
        tcp_layout.addWidget(QLabel("端口:"))
        default_port = str(self.config.get('tcp', {}).get('port', 502))
        self.port = QLineEdit(default_port)
        tcp_layout.addWidget(self.port)
        tcp_layout.addWidget(QLabel("从站地址:"))
        default_slave_id = str(self.config.get('tcp', {}).get('slave_id', 1))
        self.slave_id_tcp = QLineEdit(default_slave_id)
        tcp_layout.addWidget(self.slave_id_tcp)
        tcp_layout.addStretch(1)
        self.settings_stack.addWidget(tcp_widget)

    def create_rtu_settings_page(self):
        rtu_widget = QWidget()
        rtu_layout = QHBoxLayout(rtu_widget)
        rtu_layout.addSpacing(10)
        rtu_layout.addWidget(QLabel("串口:"))
        rtu_layout.addWidget(self.serial_port)
        rtu_layout.addWidget(QLabel("波特率:"))
        rtu_layout.addWidget(self.baud_rate)
        rtu_layout.addWidget(QLabel("数据位:"))
        rtu_layout.addWidget(self.data_bits)
        rtu_layout.addWidget(QLabel("停止位:"))
        rtu_layout.addWidget(self.stop_bits)
        rtu_layout.addWidget(QLabel("校验:"))
        rtu_layout.addWidget(self.parity)
        rtu_layout.addWidget(QLabel("从站地址:"))
        rtu_layout.addWidget(self.slave_id_rtu)
        rtu_layout.addStretch(1)
        self.settings_stack.addWidget(rtu_widget)

    def add_display_area(self, parent_splitter):
        # 创建一个垂直分割器作为主容器
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # Info area
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_header = QHBoxLayout()
        info_layout.setContentsMargins(10, 0, 10, 0)
        info_header.addWidget(QLabel("信息:"))
        info_header.addStretch(1)
        info_header.addWidget(self.clear_info_button)
        info_layout.addLayout(info_header)
        info_layout.setContentsMargins(10, 0, 10, 0)
        info_layout.addWidget(self.log_output)
        main_splitter.addWidget(info_widget)

        # Packet area
        packet_widget = QWidget()
        packet_layout = QVBoxLayout(packet_widget)
        packet_layout.setContentsMargins(10, 0, 10, 0)

        # 创建分割器
        packet_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 发送区域
        sent_widget = QWidget()
        sent_layout = QVBoxLayout(sent_widget)
        sent_layout.setContentsMargins(0, 0, 0, 0)
        #sent_layout.setSpacing(0)  # 设置垂直间距为0
        sent_header = QHBoxLayout()
        #sent_header.setContentsMargins(0, 0, 0, 0)
        sent_header.addWidget(QLabel("发送的报文:"))

        sent_layout.addLayout(sent_header)
        sent_layout.addWidget(self.sent_packet_display)
        packet_splitter.addWidget(sent_widget)

        # 接收区域
        received_widget = QWidget()
        received_layout = QVBoxLayout(received_widget)
        received_layout.setContentsMargins(0, 0, 0, 0)
        #received_layout.setSpacing(0)  # 设置垂直间距为0
        received_header = QHBoxLayout()
        #received_header.setContentsMargins(0, 0, 0, 0)
        received_header.addWidget(QLabel("接收的报文:"))

        received_layout.addLayout(received_header)
        received_layout.addWidget(self.received_packet_display)
        packet_splitter.addWidget(received_widget)
        packet_layout.addWidget(packet_splitter)

        main_splitter.addWidget(packet_widget)


        # 将主分割器添加到父布局
        parent_splitter.addWidget(main_splitter)
        return main_splitter

    def add_polling_settings(self, parent_layout):
        polling_layout = QHBoxLayout()
        polling_layout.addStretch(1)
        polling_layout.addWidget(QLabel("轮询间隔 (ms):"))
        polling_layout.addSpacing(10)
        polling_layout.addWidget(self.polling_interval_input)
        polling_layout.addStretch(1)
        polling_layout.addWidget(self.start_polling_button)
        polling_layout.addWidget(self.stop_polling_button)
        polling_layout.addStretch(1)
        parent_layout.addLayout(polling_layout)




    def on_connection_type_changed(self, index):
        self.settings_stack.setCurrentIndex(index)
        if index == 0:  # TCP
            self.load_tcp_settings()
        else:  # RTU
            self.load_rtu_settings()

    def closeEvent(self, event):
        self.save_window_state()
        super().closeEvent(event)

    def save_window_state(self):
        settings = QSettings("ModbusBaby", "WindowState")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def restore_window_state(self):
        settings = QSettings("ModbusBaby", "WindowState")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
    def create_ui_elements(self):
        # 标题
        self.title_label = QLabel("😄大牛大巨婴👌")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Logo
        self.logo_label = QLabel()
        # 设置所有输入框和下拉框的固定高度
        default_height = 28  # 你可以根据需要调整这个值

        # 连接类型选择
        self.connection_type = QComboBox()
        self.connection_type.addItems(["Modbus TCP", "Modbus RTU"])
        # 移除固定高度，让下拉框根据内容自动调整
        self.connection_type.setMaximumWidth(140)
        self.connection_type.currentIndexChanged.connect(self.on_connection_type_changed)

        # 设置默认连接类型
        default_connection_type = self.config.get('default_connection_type', 'TCP')
        self.connection_type.setCurrentText(f"Modbus {default_connection_type}")

        self.connect_button = QPushButton("连接")
        self.connect_button.clicked.connect(self.toggle_connection)


        # 修改 settings_stack 的创建和设置
        self.settings_stack = QStackedWidget()
        self.settings_stack.setContentsMargins(0, 0, 0, 0)

        # TCP 设置元素
        self.ip_address = QLineEdit()
        self.ip_address.setFixedHeight(default_height)

        self.port = QLineEdit()
        self.port.setFixedWidth(60)
        self.port.setFixedHeight(default_height)

        self.slave_id_tcp = QLineEdit()
        self.slave_id_tcp.setFixedWidth(90)
        self.slave_id_tcp.setFixedHeight(default_height)

        # RTU 设置元素
        self.serial_port = QComboBox()
        self.serial_port.setFixedWidth(250)
        # 移除固定高度，让下拉框根据内容自动调整

        self.baud_rate = QComboBox()
        self.baud_rate.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_rate.setFixedWidth(90)
        # 移除固定高度，让下拉框根据内容自动调整

        self.data_bits = QComboBox()
        self.data_bits.addItems(["8", "7"])
        self.data_bits.setFixedWidth(60)
        # 移除固定高度，让下拉框根据内容自动调整

        self.stop_bits = QComboBox()
        self.stop_bits.addItems(["1", "2"])
        self.stop_bits.setFixedWidth(60)
        # 移除固定高度，让下拉框根据内容自动调整

        self.parity = QComboBox()
        self.parity.addItems(["None", "Even", "Odd"])
        self.parity.setFixedWidth(80)
        # 移除固定高度，让下拉框根据内容自动调整

        self.slave_id_rtu = QLineEdit()
        self.slave_id_rtu.setFixedWidth(80)
        self.slave_id_rtu.setFixedHeight(default_height)

        # 操作区域
        # 地址输入框
        self.start_address_input = QLineEdit("1")
        self.start_address_input.setFixedWidth(80)
        self.start_address_input.setFixedHeight(default_height)
        self.end_address_input = QLineEdit("32")
        self.end_address_input.setFixedWidth(80)
        self.end_address_input.setFixedHeight(default_height)
        # 设置地址输入框的验证器
        address_validator = QIntValidator(0, 65535, self)
        self.start_address_input.setValidator(address_validator)
        self.end_address_input.setValidator(address_validator)

        self.register_type_combo = QComboBox()
        self.register_type_combo.addItems(['Holding Register', 'Input Register', 'Discrete Input', 'Coil', 'Report Slave ID (FC11H)'])
        self.register_type_combo.currentTextChanged.connect(self.update_data_type_visibility)
        self.register_type_combo.setFixedWidth(200)  # 增加宽度以适应新选项
        # 移除固定高度，让下拉框根据内容自动调整

        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(['BYTE', 'INT16', 'UINT16', 'INT32', 'UINT32', 'INT64', 'UINT64', 'FLOAT32', 'FLOAT64', 'BOOL', 'ASCII', 'UNIX_TIMESTAMP'])
        self.data_type_combo.setFixedWidth(120)  # 增加宽度以适应新数据类型
        # 移除固定高度，让下拉框根据内容自动调整

        self.byte_order_combo = QComboBox()
        self.byte_order_combo.addItems(['AB', 'BA'])
        self.byte_order_combo.setToolTip("字节序: AB (Big Endian), BA (Little Endian)")
        self.byte_order_combo.setFixedWidth(80)
        self.byte_order_combo.currentTextChanged.connect(self.update_byte_order)
        # 移除固定高度，让下拉框根据内容自动调整

        self.word_order_combo = QComboBox()
        self.word_order_combo.addItems(['1234', '4321'])
        self.word_order_combo.setToolTip("字序: 1234 (Big Endian), 4321 (Little Endian)")
        self.word_order_combo.setFixedWidth(80)
        self.word_order_combo.currentTextChanged.connect(self.update_word_order)
        # 移除固定高度，让下拉框根据内容自动调整

        self.read_button = QPushButton("读取")
        self.read_button.setEnabled(False)
        self.read_button.clicked.connect(self.read_register)

        self.value_input = QLineEdit()
        self.value_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.value_input.setFixedHeight(default_height)

        self.write_button = QPushButton("写入")
        self.write_button.setEnabled(False)
        self.write_button.clicked.connect(self.write_register)

        # 报文显示区域

        self.sent_packet_display = QTextEdit()
        self.sent_packet_display.setReadOnly(True)
        self.received_packet_display = QTextEdit()
        self.received_packet_display.setReadOnly(True)
        # 设置两个文本框的高度相同
        self.sent_packet_display.setMinimumHeight(150)  # 设置最小高度
        self.received_packet_display.setMinimumHeight(150)  # 设置最小高度
        # 日志输出
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        #self.sent_packet_display.setStyleSheet("background-color: #f0f0f0;")
        #self.received_packet_display.setStyleSheet("background-color: #e0e0e0;")
        # 清空按钮
        self.clear_info_button = QPushButton("清空")
        self.clear_info_button.clicked.connect(self.clear_all)

        # 轮询设置
        self.polling_interval_input = QLineEdit(str(self.config.get('polling_interval', 1000)))
        self.polling_interval_input.setFixedHeight(default_height)
        self.start_polling_button = QPushButton("开始轮询")
        self.start_polling_button.setEnabled(False)
        self.start_polling_button.clicked.connect(self.start_polling)
        self.stop_polling_button = QPushButton("停止轮询")
        self.stop_polling_button.setEnabled(False)
        self.stop_polling_button.clicked.connect(self.stop_polling)

        self.stop_polling_button.setEnabled(False)



    def update_byte_order(self, order):
        self.byte_order = 'big' if order == 'AB' else 'little'

    def update_word_order(self, order):
        self.word_order = 'big' if order == '1234' else 'little'

    def get_timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def get_timestamp_with_operation(self, operation):
        timestamp = self.get_timestamp()
        return f"{timestamp} {operation}"

    def toggle_connection(self):
        if not self.is_connected:
            self.connect_to_device()
        else:
            self.disconnect_from_device()

    def connect_to_device(self):
        if self.is_connected:
            self.logger.info("已经连接，忽略此次连接请求")
            return
        self.logger.info("连接按钮被点击")
        if self.modbus_debugger is None:
            self.logger.error("ModbusDebugger 实例不存在")
            return

        try:
            if self.connection_type.currentText() == "Modbus TCP":
                ip = self.ip_address.text()
                port = int(self.port.text())
                slave_id = int(self.slave_id_tcp.text())
                if not 0 <= slave_id <= 247:
                    raise ValueError("从站地址必须在 0-247 范围内")
                success = self.modbus_debugger.connect_tcp(ip, port, slave_id)
            else:  # Modbus RTU
                port = self.serial_port.currentText()
                baud_rate = int(self.baud_rate.currentText())
                data_bits = int(self.data_bits.currentText())
                stop_bits = int(self.stop_bits.currentText())
                parity = self.parity.currentText()
                slave_id = int(self.slave_id_rtu.text())
                if not 0 <= slave_id <= 247:
                    raise ValueError("从站地址必须在 0-247 范围内")
                success = self.modbus_debugger.connect_rtu(port, baud_rate, data_bits, stop_bits, parity, slave_id)

            if success:
                self.is_connected = True
                self.connect_button.setText("断开")
                self.log_output.append(f"{self.connection_type.currentText()} 连接成功")
                # 启用操作按钮
                self.read_button.setEnabled(True)
                self.write_button.setEnabled(True)
                self.start_polling_button.setEnabled(True)
            else:
                self.log_output.append(f"{self.connection_type.currentText()} 连接失败")
        except Exception as e:
            self.logger.error(f"连接时发生错误: {str(e)}")
            self.log_output.append(f"连接错误: {str(e)}")

    def disconnect_from_device(self):
        if not self.is_connected:
            self.logger.info("当前未连接，忽略此次断开请求")
            return
        if self.modbus_debugger and self.modbus_debugger.client:
            try:
                self.modbus_debugger.client.close()
                self.is_connected = False
                self.connect_button.setText("连接")
                self.log_output.append("已断开连接")
                # 禁用操作按钮
                self.read_button.setEnabled(False)
                self.write_button.setEnabled(False)
                self.start_polling_button.setEnabled(False)
                self.stop_polling_button.setEnabled(False)
                # 确保停止轮询
                is_polling = self.polling_timer.isActive()
                if is_polling:
                    self.stop_polling()
                    self.log_output.append("停止轮询")

            except Exception as e:
                self.logger.error(f"断开连接时发生错误: {str(e)}")
                self.log_output.append(f"断开连接错误: {str(e)}")
        else:
            self.logger.warning("尝试断开连接，但客户端不存在")
            self.log_output.append("无法断开连接：客户端不存在")

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

    def clear_all(self):
        self.clear_info()
        self.clear_packets()

    def copy_packets(self):
        clipboard = QApplication.clipboard()
        text = f"发送的报文:\n{self.sent_packets.toPlainText()}\n\n接收的报文:\n{self.received_packets.toPlainText()}"
        clipboard.setText(text)

    def read_register(self):
        if not self.is_connected:
            self.logger.error("未连接到设备")
            self.log_output.append("错误：未连接到设备")
            return
        if self.modbus_debugger:

            try:
                start_address = int(self.start_address_input.text())
                end_address = int(self.end_address_input.text())
                slave_id = int(self.slave_id_tcp.text() if self.connection_type.currentText() == "Modbus TCP" else self.slave_id_rtu.text())
                self.logger.debug(f"Reading register with slave ID: {slave_id}")   
                if not 0 <= slave_id <= 247:
                    raise ValueError("从站地址必须在 0-247 范围内")

                register_type = self.register_type_combo.currentText()
                data_type = self.data_type_combo.currentText()

                count = end_address - start_address + 1
                # 根据数据类型调整读取的寄存器数量
                registers_per_value = 1
                if data_type in ['INT32', 'UINT32', 'FLOAT32']:
                    registers_per_value = 2
                elif data_type in ['INT64', 'UINT64', 'FLOAT64']:
                    registers_per_value = 4

                # 确保读取的寄存器数量是正确的倍数
                count = max(count, registers_per_value)
                if count % registers_per_value != 0:
                    count = (count // registers_per_value + 1) * registers_per_value

                self.logger.debug(f"尝试读取 - 类型: {register_type}, 起始地址: {start_address}, 数量: {count}, 数据类型: {data_type}")

                if register_type == 'Holding Register':
                    result, sent_packet, received_packet = self.modbus_debugger.read_holding_registers(
                        start_address, count, slave_id, data_type,
                        byte_order=self.byte_order, word_order=self.word_order
                    )
                elif register_type == 'Input Register':
                    result, sent_packet, received_packet = self.modbus_debugger.read_input_registers(
                        start_address, count, slave_id, data_type,
                        byte_order=self.byte_order, word_order=self.word_order
                    )
                elif register_type == 'Discrete Input':
                    result, sent_packet, received_packet = self.modbus_debugger.read_discrete_inputs(
                        start_address, count, slave_id
                    )
                elif register_type == 'Coil':
                    result, sent_packet, received_packet = self.modbus_debugger.read_coils(
                        start_address, count, slave_id
                    )
                elif register_type == 'Report Slave ID (FC11H)':
                    # FC11H报告从站ID，不需要地址和数量参数
                    result, sent_packet, received_packet = self.modbus_debugger.report_slave_id(slave_id)
                else:
                    self.logger.error(f"不支持的寄存器类型: {register_type}")
                    return

                # 处理报文显示
                send_time = self.get_timestamp_with_operation(": READ")
                receive_time = self.get_timestamp_with_operation(": READ")

                formatted_sent = self.modbus_debugger.format_packet(sent_packet)
                formatted_received = self.modbus_debugger.format_packet(received_packet)

                self.sent_packets.append(f"{send_time}\n{formatted_sent}")
                self.received_packets.append(f"{receive_time}\n{formatted_received}")

                self.update_packet_display()

                if result is not None:
                    self.logger.debug(f"读取成功 - 结果: {result}")
                    if register_type == 'Report Slave ID (FC11H)':
                        # FC11H返回的是设备信息列表
                        formatted_result = '\n'.join(result) if isinstance(result, list) else str(result)
                        self.value_input.setText(formatted_result)
                        self.log_output.append(f"FC11H设备信息:\n{formatted_result}")
                    elif register_type in ['Discrete Input', 'Coil']:
                        formatted_result = self.format_result(result, 'BOOL')
                        self.value_input.setText(formatted_result)
                        self.log_output.append(f"读取 {register_type} {start_address}-{end_address}: {formatted_result}")
                    else:
                        formatted_result = self.format_result(result, data_type)
                        self.value_input.setText(formatted_result)
                        self.log_output.append(f"读取 {register_type} {start_address}-{end_address}: {formatted_result}")
                else:
                    if register_type == 'Report Slave ID (FC11H)':
                        self.logger.error("FC11H操作失败")
                        self.log_output.append("FC11H操作失败")
                    else:
                        self.logger.error(f"读取 {register_type} {start_address}-{end_address} 失败")
                        self.log_output.append(f"读取 {register_type} {start_address}-{end_address} 失败")

            except Exception as e:
                self.log_output.append(f"读取操作发生错误: {repr(e)}")
        else:
            self.logger.error(f"读取操作发生错误: {str(e)}")
            self.log_output.append(f"读取操作发生错误: {str(e)}")

    def write_register(self):
        if not self.is_connected:
            self.logger.error("未连接到设备")
            self.log_output.append("错误：未连接到设备")
            return
        if not self.modbus_debugger or not self.modbus_debugger.client:
            self.log_output.append("错误：Modbus 客户端未连接")
            return

        start_address = int(self.start_address_input.text())
        end_address = int(self.end_address_input.text())
        register_type = self.register_type_combo.currentText()
        data_type = self.data_type_combo.currentText()
        value = self.value_input.text()
        #values = self.data_processor.process_input_data(value, data_type, self.byte_order, self.word_order)
        slave_id = int(self.slave_id_tcp.text() if self.connection_type.currentText() == "Modbus TCP" else self.slave_id_rtu.text())

        if not 0 <= slave_id <= 247:
            raise ValueError("从站地址必须在 0-247 范围内")


        try:
            count = end_address - start_address + 1
            # 根据数据类型处理输入值
            if register_type == 'Coil':
                values = [bool(int(v.strip())) for v in value.split(',')]
                success, message, result = self.modbus_debugger.write_coils(
                    start_address, values, slave_id
                )
            elif register_type == 'Holding Register':
                if data_type == 'BYTE':
                    values = [int(v.strip()) & 0xFF for v in value.split(',')]
                elif data_type in ['FLOAT32', 'FLOAT64']:
                    values = [float(v.strip()) for v in value.split(',')]
                elif data_type in ['INT16','INT32','INT64']:
                    values = [int(v.strip()) for v in value.split(',')]
                elif data_type in ['UINT16', 'UINT32','UINT64']:  # 修改：单独处理 UINT 类型
                    values = []
                    for v in value.split(','):
                        int_value = int(v.strip())
                        if int_value < 0:
                            raise ValueError(f"UINT 类型不能写入负数: {int_value}")
                        values.append(int_value)
                elif data_type == 'BOOL':
                    values = [bool(int(v.strip())) for v in value.split(',')]
                elif data_type == 'ASCII':
                    # ASCII字符串转换为寄存器值
                    ascii_str = value.strip()
                    values = []
                    # 每两个字符组成一个寄存器
                    for i in range(0, len(ascii_str), 2):
                        if i + 1 < len(ascii_str):
                            high_byte = ord(ascii_str[i])
                            low_byte = ord(ascii_str[i + 1])
                            values.append((high_byte << 8) | low_byte)
                        else:
                            # 奇数个字符，最后一个字符放在高字节
                            values.append(ord(ascii_str[i]) << 8)
                elif data_type == 'UNIX_TIMESTAMP':
                    if value.strip().lower() == 'now':
                        # 使用当前系统时间
                        import time
                        timestamp = int(time.time())
                    else:
                        # 解析用户输入的时间戳
                        timestamp = int(value.strip())
                    # 32位时间戳分解为两个16位寄存器
                    values = [(timestamp >> 16) & 0xFFFF, timestamp & 0xFFFF]
                else:
                    self.log_output.append(f"错误：不支持的数据类型 {data_type}")
                    return
                success, message, result = self.modbus_debugger.write_registers(
                    start_address, values, slave_id, data_type,
                    byte_order=self.byte_order, word_order=self.word_order
                )

            elif register_type == 'Read/Write Multiple (FC11H)':
                # FC11H同时读写，这里实现写入功能
                success, message, result = self.modbus_debugger.read_write_multiple_registers(
                    start_address, count, start_address, values, slave_id, data_type,
                    byte_order=self.byte_order, word_order=self.word_order
                )
            elif register_type in ['Input Register', 'Discrete Input'] :
                self.log_output.append(f"错误：{register_type} 不支持写操作")
                return
            else:
                self.log_output.append(f"错误：未知的寄存器类型 {register_type}")
                return

            self.logger.debug(f"Write operation result: {result}")  # 添加这行来记录 result 的内容
            # 信息显示
            if success:
                self.log_output.append(f"成功写入 {register_type} {start_address}-{end_address}: {value}")
            else:
                self.log_output.append(f"写入失败: {message}")

            # 处理报文显示
            if result and isinstance(result, tuple) and len(result) == 2:
                sent_packet, received_packet = result
                send_time = self.get_timestamp_with_operation(": WRITE")
                receive_time = self.get_timestamp_with_operation(": WRITE")

                formatted_sent = self.modbus_debugger.format_packet(sent_packet)
                formatted_received = self.modbus_debugger.format_packet(received_packet)

                self.sent_packets.append(f"[{send_time}]\n{formatted_sent}")
                self.received_packets.append(f"{receive_time}\n{formatted_received}")
                self.update_packet_display()
                self.logger.debug("报文已添加到显示列表")
            else:
                self.logger.warning(f"无法获取发送或接收的报文，result类型: {type(result)}, 内容: {result}")
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
        if not self.is_connected:
            self.logger.error("未连接到设备，无法开始轮询")
            self.log_output.append("错误：未连接到设备，无法开始轮询")
            return
        interval = int(self.polling_interval_input.text())
        self.polling_timer.start(interval)
        self.start_polling_button.setEnabled(False)
        self.stop_polling_button.setEnabled(True)
        self.log_output.append("开始轮询")

    def stop_polling(self):
        self.polling_timer.stop()
        self.stop_polling_button.setEnabled(False)
        if self.is_connected:
            self.start_polling_button.setEnabled(True)
        else:
            self.start_polling_button.setEnabled(False)
        self.log_output.append("停止轮询")
    def poll_register(self):
        if not self.is_connected:
            self.logger.error("未连接到设备")
            self.log_output.append("错误：未连接到设备")
            self.stop_polling()  # 停止轮询
            return
        if self.modbus_debugger:
            try:
                start_address = int(self.start_address_input.text())
                end_address = int(self.end_address_input.text())
                register_type = self.register_type_combo.currentText()
                data_type = self.data_type_combo.currentText()
                slave_id = int(self.slave_id_tcp.text() if self.connection_type.currentText() == "Modbus TCP" else self.slave_id_rtu.text())
                count = end_address - start_address + 1

                # 根据数据类型调整读取的寄存器数量
                registers_per_value = 1
                if data_type in ['INT32', 'UINT32', 'FLOAT32', 'UNIX_TIMESTAMP']:
                    registers_per_value = 2
                elif data_type in ['INT64', 'UINT64','FLOAT64']:
                    registers_per_value = 4
                elif data_type == 'ASCII':
                    # ASCII类型保持用户指定的寄存器数量
                    registers_per_value = 1

                # 确保读取的寄存器数量是正确的倍数
                count = max(count, registers_per_value)
                if count % registers_per_value != 0:
                    count = (count // registers_per_value + 1) * registers_per_value
           
                if register_type == 'Holding Register':
                    result, sent_packet, received_packet = self.modbus_debugger.read_holding_registers(start_address, count, slave_id)
                elif register_type == 'Input Register':
                    result, sent_packet, received_packet = self.modbus_debugger.read_input_registers(start_address, count, slave_id)
                elif register_type == 'Discrete Input':
                    result, sent_packet, received_packet = self.modbus_debugger.read_discrete_inputs(start_address, count, slave_id)
                elif register_type == 'Coil':
                    result, sent_packet, received_packet = self.modbus_debugger.read_coils(start_address, count, slave_id)

                # 添加时间戳
                send_time = self.get_timestamp_with_operation(": POLLING")
                receive_time = self.get_timestamp_with_operation(": POLLING")
                formatted_sent = self.modbus_debugger.format_packet(sent_packet)
                formatted_received = self.modbus_debugger.format_packet(received_packet)

                self.sent_packets.append(f"{send_time}\n{formatted_sent}")
                self.received_packets.append(f"{receive_time}\n{formatted_received}")

                self.update_packet_display()

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
            except Exception as e:
                self.logger.error(f"轮询操作发生错误: {str(e)}")
                self.log_output.append(f"轮询操作发生错误: {str(e)}")
                self.stop_polling()  # 如果发生错误，也停止轮询
        else:
            self.logger.error("ModbusDebugger 实例不存在")
            self.log_output.append("错误：ModbusDebugger 实例不存在")
            self.stop_polling()  # 如果 ModbusDebugger 不存在，停止轮询


    def format_result(self, result, data_type):

        if data_type == 'BOOL':
            return ', '.join('1' if bit else '0' for bit in result)
        elif data_type == 'BYTE':
            return ', '.join(f"{x:02X}" for x in result)
        elif data_type in ['INT16', 'UINT16', 'INT32', 'UINT32', 'INT64', 'UINT64']:
            return ', '.join(map(str, result))
        elif data_type in ['FLOAT32', 'FLOAT64']:
            return ', '.join(f"{x:.6f}" for x in result)
        elif data_type == 'ASCII':
            return str(result[0]) if result else ""
        elif data_type == 'UNIX_TIMESTAMP':
            return str(result[0]) if result else ""
        else:
            return str(result)
    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            self.update_packet_display()
        super().changeEvent(event)

    def append_colored_text(self, text_edit, text):
        try:
            cursor = text_edit.textCursor()
            palette = QApplication.palette()
            is_dark_mode = palette.color(QPalette.ColorRole.Window).lightness() < 128
            default_color = palette.color(QPalette.ColorRole.Text)

            format_time = QTextCharFormat()
            if is_dark_mode:
                format_time.setForeground(QColor(0, 255, 255))  # 深色模式使用青色
            else:
                format_time.setForeground(QColor("blue"))  # 浅色模式使用蓝色

            format_data = QTextCharFormat()
            format_data.setForeground(default_color)

            lines = text.split('\n', 1)
            if len(lines) > 0:
                cursor.insertText(lines[0] + '\n', format_time)
                if len(lines) > 1:
                    cursor.insertText(lines[1], format_data)
            text_edit.append("")
        except Exception as e:
            # 如果彩色文本失败，使用简单的文本追加
            text_edit.append(text)

    def update_packet_display(self):

       # print(f"开始更新报文显示: 发送 {len(self.sent_packets)}, 接收 {len(self.received_packets)}")

        self.sent_packet_display.clear()
        self.received_packet_display.clear()

        #self.sent_packet_display.append("发送：")
        for packet in self.sent_packets:

            self.append_colored_text(self.sent_packet_display,  packet)
        #self.received_packet_display.append("接收：")
        for packet in self.received_packets:

            self.append_colored_text(self.received_packet_display, packet)



        # 滚动到底部
        self.sent_packet_display.verticalScrollBar().setValue(
            self.sent_packet_display.verticalScrollBar().maximum()
        )
        self.received_packet_display.verticalScrollBar().setValue(
            self.received_packet_display.verticalScrollBar().maximum()
        )

        # 安全地更新显示
        try:
            self.sent_packet_display.update()
            self.received_packet_display.update()
        except Exception as e:
            self.logger.debug(f"更新显示时出现错误: {e}")


    def clear_info(self):
        self.log_output.clear()


    def clear_packets(self):
        self.sent_packet_display.clear()
        self.received_packet_display.clear()
        self.sent_packets.clear()
        self.received_packets.clear()

    def load_tcp_settings(self):
        tcp_config = self.config.get('tcp', {})
        self.ip_address.setText(tcp_config.get('ip', 'localhost'))
        self.port.setText(str(tcp_config.get('port', 502)))
        self.slave_id_tcp.setText(str(tcp_config.get('slave_id', 1)))

    def load_rtu_settings(self):
        rtu_config = self.config.get('rtu', {})
        self.update_serial_ports()
        self.baud_rate.setCurrentText(str(rtu_config.get('baud_rate', 9600)))
        self.data_bits.setCurrentText(str(rtu_config.get('data_bits', 8)))
        self.stop_bits.setCurrentText(str(rtu_config.get('stop_bits', 1)))
        self.parity.setCurrentText(rtu_config.get('parity', 'None'))
        self.slave_id_rtu.setText(str(rtu_config.get('slave_id', 1)))


    #def update_serial_ports(self,default_port=None):
    def update_serial_ports(self, default_port=None):
        self.logger.info("开始更新串口列表")
        self.serial_port.clear()

        system_ports = self.get_system_serial_ports()

        if system_ports:
            self.serial_port.addItems(system_ports)
            if default_port and default_port in system_ports:
                self.serial_port.setCurrentText(default_port)
            else:
                self.serial_port.setCurrentIndex(len(system_ports) - 1)  # 选择最后一个串口
            self.logger.info(f"串口列表更新完成，当前选中: {self.serial_port.currentText()}")
        else:
            self.logger.info("未检测到可用串口")
            self.log_output.append("未检测到可用串口")

    def get_system_serial_ports(self):
        try:
            if self.modbus_debugger is None:
                self.logger.info("初始化 ModbusDebugger 实例")
                self.modbus_debugger = ModbusDebugger(self.config)
            ports = self.modbus_debugger.get_available_serial_ports()
            self.logger.info(f"系统检测到的串口: {ports}")
            return ports
        except Exception as e:
            self.logger.error(f"获取系统串口列表时出错: {str(e)}")
            return []



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModbusBabyGUI()
    window.show()
    sys.exit(app.exec())
