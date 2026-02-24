# custom_components/ecto/const.py
DOMAIN = "ecto_modbus"
DEFAULT_BAUDRATE = 19200
DEVICE_TYPES = [
    "binary_sensor_10ch",
    "relay_10ch",
    "temperature_sensor"
]

PORT_TYPE_SERIAL = "serial"
PORT_TYPE_RS485 = "rs485"
DEFAULT_PORT_TYPE = PORT_TYPE_RS485
PORT_TYPES = [PORT_TYPE_SERIAL, PORT_TYPE_RS485]