# Ectocontrol Modbus Integration
Home Assistant Custom Component for Ectocontrol RS485 devices


# configuration.yaml
```
ecto_modbus:
    port: /dev/ttyUSB0
    devices:
        - type: temperature_sensor
          addr: 4
          entity_id: sensor.living_room_temperature
        - type: binary_sensor_10ch
          addr: 3
```