import sys
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

def run_server(host='0.0.0.0', port=502):
    # 创建一个数据存储
    store = ModbusSlaveContext()
    context = ModbusServerContext(slaves=store, single=True)

    print(f"Starting Modbus TCP Server on {host}:{port}...")
    try:
        StartTcpServer(
            context=context,
            address=(host, port)
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        print("If using port 502, try running with sudo.")
        sys.exit(1)

if __name__ == "__main__":
    run_server()