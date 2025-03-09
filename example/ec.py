#!/usr/bin/env python
import asyncio
import getopt
import struct
import sys
import threading

import aioesphomeapi
import modbus_tk
import modbus_tk.defines as cst
from aioesphomeapi import EntityState
from modbus_tk import modbus_rtu
from modbus_tk.modbus import Slave
from modbus_tk.modbus_rtu import RtuServer
from serial import rs485


def pack_float(f):
    byte_array = struct.pack(">f", f)

    res = [
        struct.unpack(">H", byte_array[0:2])[0],
        struct.unpack(">H", byte_array[2:4])[0]
    ]
    return res


def async_to_sync(awaitable):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(awaitable)


class ModbusConfig:

    def __init__(self, argv):
        self.main_port = "/dev/ttyACM0"
        self.energy_port = "/dev/ttyUSB0"
        self.esp_ip = "192.168.3.95"
        self.esp_port = 6053
        self.esp_key = "1XhABs3HkIf6Znf7PXt2NA0mCIb8XkHZYOKDM4nEBUk="
        arg_help = "{0} -i <input> -u <user> -o <output>".format(argv[0])

        try:
            opts, args = getopt.getopt(argv[1:], "hi:mp:ep:",
                                       ["help", "main-port=", "esp-ip=", "esp-key=", "energy-port="])
        except:
            print(arg_help)
            sys.exit(2)

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(arg_help)  # print the help message
                sys.exit(2)
            elif opt in ("-ep", "--energy-port"):
                self.energy_port = arg
            elif opt in ("-mp", "--main-port"):
                self.main_port = arg
            elif opt == "--esp-ip":
                self.esp_ip = arg
            elif opt == "--esp-key":
                self.esp_port = arg


class ESPHomeDevice:

    def __init__(self, ip: str, port: int, key: str):
        """Connect to an ESPHome device and wait for state changes."""
        self.sensors = {}
        self.ids = {}
        self.listeners = {}
        self.last_state = {}
        cli = aioesphomeapi.APIClient(
            address=ip,
            port=port,  # 6053,
            password=None,
            noise_psk=key  # "mY2PuxeI7kVcAZIITrg+sOE6UOCP1TYNmWBdlmjxP94=",
        )
        async_to_sync(cli.connect(login=True))
        self.cli = cli
        esp_sensors = async_to_sync(cli.list_entities_services())[0]
        for sensor in esp_sensors:
            print(sensor)
            self.sensors[sensor.object_id] = sensor.key
            self.ids[sensor.key] = sensor.object_id
        cli.subscribe_states(self.handle_update)

    def add_callback(self, object_id, fn):
        key = self.sensors[object_id]
        self.listeners[key] = fn

    def handle_update(self, state: EntityState):
        if state.state != self.last_state.get(state.key):
            print("Handle object Update state")
            fn = self.listeners.get(state.key)
            self.last_state[state.key] = state.state
            if fn is not None:
                fn(state.state)

    def get_cli(self):
        return self.cli


class ModBusRegisterSensorOld:

    def __init__(self, slave, reg_addr, multiplier, object_it):
        self.regAddr = reg_addr
        self.multiplier = multiplier
        self.slave = slave
        self.reg_block = "DATA"
        self.value = None
        self.object_id = object_it

    def set_reg_block(self, reg_block):
        self.reg_block = reg_block

    def set_value(self, value):
        if value != self.value:
            self.value = value
            print("Set value=" + str(value) + " for param=" + self.object_id)
            self.slave.set_values(self.reg_block, self.regAddr, pack_float(value * self.multiplier))

    def get_object_id(self):
        return self.object_id


class EnergyMeter:
    online: bool

    esp_voltageA: ModBusRegisterSensorOld
    esp_voltageB: ModBusRegisterSensorOld
    esp_voltageC: ModBusRegisterSensorOld

    esp_powerA: ModBusRegisterSensorOld
    esp_powerB: ModBusRegisterSensorOld
    esp_powerC: ModBusRegisterSensorOld
    esp_powerTotal: ModBusRegisterSensorOld

    esp_currentA: ModBusRegisterSensorOld
    esp_currentB: ModBusRegisterSensorOld
    esp_currentC: ModBusRegisterSensorOld

    esp_totalConsumed: ModBusRegisterSensorOld

    def __init__(self, slave, esp: ESPHomeDevice):
        self.sensors = {}
        self.slave = slave
        self.init()
        self.esp_totalConsumed = ModBusRegisterSensorOld(slave, 0x101E, 1, "Total Consumed")
        self.esp_totalConsumed.set_reg_block("Consumed")

        self.esp_powerTotal = ModBusRegisterSensorOld(slave, 0x2012, 10, "Phase Total Power")
        self.esp_powerA = ModBusRegisterSensorOld(slave, 0x2014, 10, "Phase A Power")
        self.esp_powerB = ModBusRegisterSensorOld(slave, 0x2016, 10, "Phase B Power")
        self.esp_powerC = ModBusRegisterSensorOld(slave, 0x2018, 10, "Phase C Power")

        self.esp_voltageA = ModBusRegisterSensorOld(slave, 0x2006, 10, "Phase A Voltage")
        self.esp_voltageB = ModBusRegisterSensorOld(slave, 0x2008, 10, "Phase B Voltage")
        self.esp_voltageC = ModBusRegisterSensorOld(slave, 0x200A, 10, "Phase C Voltage")

        self.esp_currentA = ModBusRegisterSensorOld(slave, 0x200C, 1000, "Phase A Current")
        self.esp_currentB = ModBusRegisterSensorOld(slave, 0x200E, 1000, "Phase B Current")
        self.esp_currentC = ModBusRegisterSensorOld(slave, 0x2010, 1000, "Phase C Current")
        esp.add_callback("phase_a_power", self.esp_powerA.set_value)
        esp.add_callback("phase_b_power", self.esp_powerB.set_value)
        esp.add_callback("phase_c_power", self.esp_powerC.set_value)

        esp.add_callback("phase_a_voltage", self.esp_voltageA.set_value)
        esp.add_callback("phase_b_voltage", self.esp_voltageB.set_value)
        esp.add_callback("phase_c_voltage", self.esp_voltageC.set_value)

        esp.add_callback("phase_a_current", self.esp_currentA.set_value)
        esp.add_callback("phase_b_current", self.esp_currentB.set_value)
        esp.add_callback("phase_c_current", self.esp_currentC.set_value)

        esp.add_callback("phase_total_power", self.esp_powerTotal.set_value)

        esp.add_callback("total_consumed", self.esp_totalConsumed.set_value)

    def init(self):
        self.slave.add_block('ID', cst.HOLDING_REGISTERS, 0, 64)
        self.slave.set_values('ID', 0,
                              [112, 701, 0, 0, 0, 0, 1, 10, 0, 0, 0, 10, 0, 0, 0, 1000, 0, 0, 1000, 0, 0, 1000, 0,
                               0,
                               1000, 1, 15, 0, 0, 0, 1000, 0, 0, 1000, 0, 0, 1000, 0, 0, 1000, 0, 0, 0, 0, 3, 3, 3,
                               41,
                               7, 8, 15, 8, 15, 1106, 517, 8963, 0, 0, 0, 0, 0, 0, 0, 0])

        self.slave.add_block('DATA', cst.HOLDING_REGISTERS, 0x2000, 50)

        self.slave.add_block('Consumed', cst.HOLDING_REGISTERS, 0x101E, 2)

        self.slave.add_block('tmp', cst.HOLDING_REGISTERS, 0x1028, 2)
        self.slave.set_values("tmp", 0x1028, [400, 0])

    def set_power_a(self, power: float):
        self.esp_powerA.set_value(power)

    def set_power_b(self, power: float):
        self.esp_powerB.set_value(power)

    def set_power_c(self, power: float):
        self.esp_powerC.set_value(power)

    def set_power_total(self, power: float):
        self.esp_powerTotal.set_value(power)

    def set_total_consumer(self, total_consumed):
        self.esp_totalConsumed.set_value(total_consumed)

    def set_voltage_a(self, voltage):
        self.esp_voltageA.set_value(voltage)

    def set_voltage_b(self, voltage):
        self.esp_voltageB.set_value(voltage)

    def set_voltage_c(self, voltage):
        self.esp_voltageC.set_value(voltage)

    def set_current_a(self, current):
        self.esp_currentA.set_value(current)

    def set_current_b(self, current):
        self.esp_currentB.set_value(current)

    def set_current_c(self, current):
        self.esp_currentC.set_value(current)


def main(config: ModbusConfig):
    """main"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # esp = ESPHomeDevice(config.esp_ip, config.esp_port, config.esp_key)
    esp_t = ESPHomeDevice("192.168.3.77", config.esp_port, "mY2PuxeI7kVcAZIITrg+sOE6UOCP1TYNmWBdlmjxP94=")
    logger = modbus_tk.utils.create_logger(name="dummy", record_format="%(message)s")

    # Create the server
    port485_main = rs485.RS485(config.main_port, baudrate=19200, inter_byte_timeout=0.002)
    # port485_energy = rs485.RS485(config.energy_port, baudrate=9600, inter_byte_timeout=0.004)
    # server9600 = modbus_rtu.RtuServer(port485_energy, interchar_multiplier=1)
    server19200 = modbus_rtu.RtuServer(port485_main, interchar_multiplier=1)

    try:

        # server9600.start()
        server19200.start()

        ext = Extender(server19200, 0x04, esp_t, [
            "kitchen_heating",
            "bathroom_heating",
            "guest_room_heating",
            "bedroom_heating",
            "childrens_room_heating",
            "hall_heating"
        ])
        # esp_slave = server9600.add_slave(3)
        # dev: EnergyMeter = EnergyMeter(esp_slave, esp)

        # esp_dev: ESPDevice = ESPDevice(esp.cli, dev)
        # for i in range(5,15):
        #     t= ThermoSensor(server19200,i)
        #     if i==14:
        #       esp_t.add_callback("esp_atc_4bf595_temperature", t.set_value)
        loop.run_forever()

    finally:
        # server9600.stop()
        server19200.stop()


class ModBusRegisterSensor:

    def __init__(self, slave: Slave, reg_type: int, addr: int, reg_size: int):
        self.block_name = "val-x" + str(addr)
        self.addr = addr
        slave.add_block(self.block_name, reg_type, addr, reg_size)
        self.slave = slave

    def set_raw_value(self, raw_value):
        self.slave.set_values(self.block_name, self.addr, raw_value)


class ModBusDevice:

    def __init__(self, server: RtuServer, slave_id: int):
        self.server = server
        self.slave = server.add_slave(slave_id)
        self.addr = slave_id
        # hooks.install_hook("modbus.Slave.handle_request", self.handle_request)

    def handle_request(self, request_pdu_t):
        # get the function code
        # print("got PDU" + request_pdu)
        request_pdu = request_pdu_t[1]
        modbus_tk.LOGGER.error("REQ: %s", request_pdu)
        (function_code,) = struct.unpack(">B", request_pdu[0:1])
        modbus_tk.LOGGER.error("REQ Code: %s", function_code)
        if function_code == 0x46:
            return struct.pack(">BB", function_code, self.addr)
        return None


class EctoDevice(ModBusDevice):

    def __init__(self, server: RtuServer, slave_id: int, dev_type):
        super(EctoDevice, self).__init__(server, slave_id)
        reg = ModBusRegisterSensor(self.slave, cst.HOLDING_REGISTERS, 0, 4)
        reg.set_raw_value([0x80, slave_id - 3, slave_id, dev_type])
        self.registers = {0: reg}


class ThermoSensor(EctoDevice):

    def __init__(self, server: RtuServer, slave_id):
        super(ThermoSensor, self).__init__(server, slave_id, 0x2201)
        reg = ModBusRegisterSensor(self.slave, cst.READ_INPUT_REGISTERS , 0x20, 1)
        self.registers[0x20] = reg

    def set_value(self, value):
        print("Set Temrature to: "+str(int(value * 10)))
        self.registers[0x20].set_raw_value([int(value * 10)])


class Extender(EctoDevice):

    def __init__(self, server: RtuServer, slave_id, esp: ESPHomeDevice, watch: []):
        self.lock = threading.Lock
        self.switch = [0, 0, 0, 0, 0, 0, 0, 0]
        super(Extender, self).__init__(server, slave_id, 0x5908)
        reg = ModBusRegisterSensor(self.slave, cst.READ_INPUT_REGISTERS, 0x10, 1)
        self.registers[0x10] = reg
        i = 1
        for a in watch:
            esp.add_callback(a, getattr(self, "set_switch_" + str(i)))
            i = i + 1

    def set_switch_1(self, state):
        self.set_switch_state(7, state)

    def set_switch_2(self, state):
        self.set_switch_state(6, state)

    def set_switch_3(self, state):
        self.set_switch_state(5, state)

    def set_switch_4(self, state):
        self.set_switch_state(4, state)

    def set_switch_5(self, state):
        self.set_switch_state(3, state)

    def set_switch_6(self, state):
        self.set_switch_state(2, state)

    def set_switch_7(self, state):
        self.set_switch_state(1, state)

    def set_switch_8(self, state):
        self.set_switch_state(0, state)

    def set_switch_state(self, num, state):
        # with self.lock:
        if state != self.switch[num]:
            print("Toggle switch " + str(num + 1) + " to " + str(state))
            value = 0
            state_value = 0
            if state:
                state_value = 1
            self.switch[num] = state_value
            for a in self.switch:
                value = (value << 1) + a
            self.set_value(value << 8)

    def set_value(self, value):
        self.registers[0x10].set_raw_value([value])


if __name__ == "__main__":
    main(ModbusConfig(sys.argv))
