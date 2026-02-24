# Ectocontrol Modbus Integration
Home Assistant Custom Component for Ectocontrol RS485 devices

## Supported Devices

| Type | Device | Channels | Description |
|------|--------|----------|-------------|
| `temperature_sensor` | EctoTemperatureSensor | 1 | Temperature input from HA entity |
| `binary_sensor_10ch` | EctoCH10BinarySensor | 10 | 10-channel contact sensor splitter |
| `relay_10ch` | EctoRelay10CH | 10 | 10-channel relay control module |

## Configuration

Add the following to your `configuration.yaml`:

```yaml
ecto_modbus:
    port: /dev/ttyUSB0
    port_type: rs485        # or 'serial'
    baudrate: 19200         # default
    devices:
        - type: temperature_sensor
          addr: 4
          entity_id: sensor.living_room_temperature
        - type: binary_sensor_10ch
          addr: 3
        - type: relay_10ch
          addr: 5
```

### Device Configuration Options

| Option | Required | Description |
|--------|----------|-------------|
| `type` | Yes | Device type: `temperature_sensor`, `binary_sensor_10ch`, or `relay_10ch` |
| `addr` | Yes | Modbus slave address (3-32) |
| `entity_id` | For temp sensor | Home Assistant entity to read temperature from |

### Port Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `port` | Required | Serial port device path |
| `port_type` | `rs485` | `rs485` or `serial` |
| `baudrate` | `19200` | Serial baud rate |

## Entities Created

### Temperature Sensor
- Reads temperature from specified HA entity
- Scales value by 10 (e.g., 22.5°C → 225)

### Binary Sensor (10-channel)
- Creates 10 switch entities for channel control
- Each channel maps to a bit in register 0x0010

### Relay (10-channel)
- Creates 10 switch entities for relay control
- Channels 0-7 in MSB byte, channels 8-9 in LSB byte
- Supports timer functionality per channel

## Example: Control Relay via Automation

```yaml
automation:
  - alias: "Turn on relay channel 0"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.device_5_ch1
```