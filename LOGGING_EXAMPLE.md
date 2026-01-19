# Modbus RT/TX Packet Logging

This document demonstrates the enhanced logging capabilities for debugging Modbus communication.

## Overview

The integration now includes comprehensive logging at multiple levels:

1. **Protocol Level**: Logs all Modbus requests (RT) and responses (TX) using modbus_tk hooks
2. **Register Level**: Logs individual register read/write operations
3. **Error Level**: Logs any Modbus protocol errors

## Log Levels

All Modbus packet logs use the `DEBUG` level, so you need to enable debug logging for the `ecto_modbus` component:

```yaml
logger:
  default: info
  logs:
    custom_components.ecto_modbus: debug
```

## Example Log Output

### Incoming Modbus Request (RT)
```
DEBUG:custom_components.ecto_modbus:RT: Slave=4, Func=3, Addr=16, Qty=1, PDU=b'\x04\x03\x00\x10\x00\x01'
```
- **Slave**: Modbus slave ID (device address)
- **Func**: Modbus function code (3 = Read Holding Registers, 4 = Read Input Registers)
- **Addr**: Starting register address
- **Qty**: Number of registers to read
- **PDU**: Raw Protocol Data Unit bytes

### Register Read Operation
```
DEBUG:custom_components.ecto_modbus.transport:RT: Reading from register - block=val-x16, addr=16 (0x10), size=1, type=INPUT
DEBUG:custom_components.ecto_modbus.transport:RT: Register read completed - block=val-x16, addr=16 (0x10), values=[32896]
```

### Outgoing Modbus Response (TX)
```
DEBUG:custom_components.ecto_modbus:TX: Slave=4, Func=4, PDU=b'\x04\x04\x02\x80\x80'
```

### Register Write Operation
```
DEBUG:custom_components.ecto_modbus.transport:TX: Writing to register - block=val-x16, addr=16 (0x10), value=[32896], type=INPUT
DEBUG:custom_components.ecto_modbus.transport:TX: Register write completed - block=val-x16, addr=16 (0x10)
```

### Modbus Error
```
ERROR:custom_components.ecto_modbus:Modbus Error: exception=ModbusIOException("CRC error"), request_pdu=b'\x04\x03\x00\x10\x00\x01'
```

## Complete Transaction Example

When a Home Assistant entity queries a 10-channel binary sensor:

```
# 1. Incoming read request from master
DEBUG:custom_components.ecto_modbus:RT: Slave=4, Func=4, Addr=16, Qty=1, PDU=b'\x04\x04\x00\x10\x00\x01'

# 2. Register level read
DEBUG:custom_components.ecto_modbus.transport:RT: Reading from register - block=val-x16, addr=16 (0x10), size=1, type=INPUT
DEBUG:custom_components.ecto_modbus.transport:RT: Register read completed - block=val-x16, addr=16 (0x10), values=[32896]

# 3. Register read callback (if configured)
DEBUG:custom_components.ecto_modbus.devices:Register 0x10 read: addr=4, value=[32896]

# 4. Outgoing response
DEBUG:custom_components.ecto_modbus:TX: Slave=4, Func=4, PDU=b'\x04\x04\x02\x80\x80'
```

## Key Features

1. **Full Visibility**: See every request and response at the protocol level
2. **Register Tracking**: Track individual register operations with hex addresses
3. **Error Diagnostics**: Detailed error logging with request context
4. **Performance**: Minimal overhead when debug logging is disabled
5. **Structured Logging**: Consistent format for easy parsing and filtering

## Troubleshooting

### No logs appearing
- Ensure debug logging is enabled for `custom_components.ecto_modbus`
- Check that the integration is loaded and devices are configured
- Verify that a Modbus master is actively polling the server

### Missing PDU data
- Some hooks may not receive the full PDU depending on the modbus_tk version
- Register-level logs will still show the actual data values

### Too many logs
- Disable debug logging when not needed: set logger to `info` or `warning`
- Use log filtering to focus on specific devices or operations
