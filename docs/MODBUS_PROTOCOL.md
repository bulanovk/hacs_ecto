# Modbus Protocol Reference: Ectocontrol Adapter v2

**Document Version:** 1.0
**Last Updated:** 2025
**Hardware:** Ectocontrol Modbus Adapter v2
**Protocol:** Modbus RTU over RS-485

---

## Table of Contents

1. [Protocol Overview](#1-protocol-overview)
2. [Communication Parameters](#2-communication-parameters)
3. [Complete Register Map](#3-complete-register-map)
4. [Data Type Reference](#4-data-type-reference)
5. [Invalid/Unsupported Value Markers](#5-invalidunsupported-value-markers)
6. [Bitfield Definitions](#6-bitfield-definitions)
7. [Command Codes](#7-command-codes)
8. [Communication Patterns](#8-communication-patterns)
9. [Error Handling](#9-error-handling)
10. [Example Transactions](#10-example-transactions)
11. [Implementation Notes](#11-implementation-notes)

---

## 1. Protocol Overview

The Ectocontrol Modbus Adapter v2 provides a Modbus RTU interface for gas boiler monitoring and control. The adapter acts as a Modbus slave device that exposes boiler status, sensors, and controls via standard Modbus holding registers.

### Hardware Requirements

| Component | Specification |
|-----------|---------------|
| **Interface** | RS-485 half-duplex |
| **Adapter** | Ectocontrol Modbus Adapter v2 |
| **Boiler Connection** | Proprietary boiler interface |
| **Cable** | Twisted pair with appropriate termination |

### Device Addressing

- **Slave ID Range:** 1-32
- **Multiple Devices:** Up to 32 adapters on a single RS-485 bus
- **Uniqueness:** Each slave ID must be unique per port

---

## 2. Communication Parameters

### Serial Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Baud Rate** | 19200 | Fixed |
| **Data Bits** | 8 | |
| **Parity** | None (N) | |
| **Stop Bits** | 1 | |
| **Mode** | Half-duplex | Requires locking |
| **Timeout** | 2.0 seconds | Default, configurable |

### Modbus Functions Used

| Function Code | Name | Usage |
|---------------|------|-------|
| 0x03 | Read Holding Registers | Reading all sensor/status registers |
| 0x04 | Read Input Registers | (Defined but unused in current implementation) |
| 0x06 | Write Single Register | Writing control registers |
| 0x10 | Write Multiple Registers | (Defined but unused in current implementation) |

### Connection Lifecycle

```
1. Open serial port at 19200/8N1
2. Create RtuMaster instance
3. Set timeout (default 2.0s)
4. Execute read/write operations
5. Close port on shutdown
```

---

## 3. Complete Register Map

All registers are 16-bit holding registers unless otherwise noted.

### 3.0 Generic Device Information Registers

All Ectocontrol devices share a common information structure at addresses 0x0000-0x0003 (holding registers).

| Address | Name | Type | Access | Description |
|---------|------|------|--------|-------------|
| 0x0000 | Reserved | u16 | RO | Reserved for future use |
| 0x0001 | UID | u24 (3 bytes) | RO | Unique device identifier (range: 0x800000-0xFFFFFF) |
| 0x0002 | Reserved + Address | u8/u8 | RO | Reserved (MSB), Device Modbus address (LSB, range: 0x01-0x20) |
| 0x0003 | Type + Channels | u8/u8 | RO | Device type (MSB), Channel count (LSB, range: 1-10) |

#### Device Type Codes (0x0003 MSB)

| Code | Device Type |
|------|-------------|
| 0x11 | OpenTherm Adapter v1 (discontinued) |
| 0x14 | **OpenTherm Adapter v2** (current boiler adapter) |
| 0x15 | eBus Adapter |
| 0x16 | Navien Adapter |
| 0x22 | Temperature Sensor |
| 0x23 | Humidity Sensor |
| 0x50 | Universal Contact Sensor |
| 0x59 | 10-channel Contact Sensor Splitter |
| 0xC0 | 2-channel Relay Control Block |
| 0xC1 | 10-channel Relay Control Block |

---

### 3.1 Status & Diagnostics Registers

| Address | Name | Type | Access | Scale | Invalid Marker | Description |
|---------|------|------|--------|-------|----------------|-------------|
| 0x0010 | Status | u16 | RO | - | - | Adapter type and communication status |
| 0x0011 | Version | u16 | RO | - | 0xFFFF | Hardware (MSB) and software (LSB) version |
| 0x0012 | Uptime High | u16 | RO | - | - | System uptime, high word (MSB of u32) |
| 0x0013 | Uptime Low | u16 | RO | - | - | System uptime, low word (LSB of u32) |

#### Register 0x0010: Status Register

```
Bits 0-2 (LSB): Adapter Type
    000 = OpenTherm
    001 = eBus
    010 = Navien
    011-111 = Reserved

Bit 3: Boiler Communication Status
    0 = No response from boiler to last command
    1 = Response received from boiler to last command

Bits 4-14: Reserved (read as 0)

Bit 15 (MSB): Last Reboot Code
    0-255 = Reboot reason code
    0 = Normal startup
    1-255 = Various reset codes
```

**Note:** The adapter type codes indicate which boiler protocol the adapter is using. This is important for determining which features are available.

#### Register 0x0011: Version Register

```
MSB (bits 8-15): Hardware version (0-255)
LSB (bits 0-7):  Software version (0-255)
```

Extract as two separate u8 values:
- `hw_version = (register_value >> 8) & 0xFF`
- `sw_version = register_value & 0xFF`

#### Register 0x0012-0x0013: Uptime Registers

Combined as a 32-bit unsigned integer (u32):
- `uptime_seconds = (register_0x0012 << 16) | register_0x0013`
- Range: 0 to 4,294,967,295 seconds (~136 years)
- Represents time since last adapter reboot/power-on

---

### 3.2 Temperature Sensor Registers

| Address | Name | Type | Access | Scale | Range | Invalid Marker | Description |
|---------|------|------|--------|-------|-------|----------------|-------------|
| 0x0018 | CH Temperature | i16 | RO | ÷10 | -3276.8 to +3276.7°C | 0x7FFF | Central heating water temperature |
| 0x0019 | DHW Temperature | u16 | RO | ÷10 | 0 to +6553.5°C | 0x7FFF | Domestic hot water temperature |
| 0x0020 | Outdoor Temperature | i8 (MSB) | RO | 1 | -128 to +127°C | 0x7F | Outside temperature |
| 0x0026 | CH Setpoint Active | i16 | RO | ÷256 | -128 to +127.99°C | 0x7FFF | Current active CH setpoint (high precision) |

#### Temperature Scaling Examples

```
CH Temperature (0x0018):
    Raw:  291  →  29.1°C    (291 / 10)
    Raw: -150  → -15.0°C    (signed: -150 / 10)
    Raw: 0x7FFF → Unavailable

DHW Temperature (0x0019):
    Raw:  425  →  42.5°C    (425 / 10)
    Raw: 0x7FFF → Unavailable

Outdoor Temperature (0x0020, MSB only):
    Raw: 0x0512 →  5°C      (MSB = 0x05)
    Raw: 0xF812 → -8°C      (MSB = 0xF8 = -8 signed)
    Raw: 0x7F12 → Unavailable (MSB = 0x7F)

CH Setpoint Active (0x0026):
    Raw:  11520 →  45.0°C   (11520 / 256)
    Raw:  11571 →  45.199°C (11571 / 256)
    Raw: 0x7FFF → Unavailable
```

---

### 3.3 System Sensor Registers

| Address | Name | Type | Access | Scale | Range | Invalid Marker | Description |
|---------|------|------|--------|-------|-------|----------------|-------------|
| 0x001A | Pressure | u8 (LSB) | RO | ÷10 | 0 to +25.5 bar | 0xFF | System water pressure |
| 0x001B | Flow Rate | u8 (LSB) | RO | ÷10 | 0 to +25.5 L/min | 0xFF | Domestic hot water flow rate |
| 0x001C | Modulation Level | u8 (LSB) | RO | 1 | 0 to 100% | 0xFF | Burner modulation percentage |

#### System Sensor Examples

```
Pressure (0x001A, LSB only):
    Raw: 0x340C → 1.2 bar  (LSB = 0x0C = 12, 12 / 10)
    Raw: 0x34FF → Unavailable (LSB = 0xFF)

Flow Rate (0x001B, LSB only):
    Raw: 0x1208 → 0.8 L/min (LSB = 0x08 = 8, 8 / 10)
    Raw: 0x12FF → Unavailable (LSB = 0xFF)

Modulation Level (0x001C, LSB only):
    Raw: 0x004B → 75% (LSB = 0x4B = 75)
    Raw: 0x00FF → Unavailable (LSB = 0xFF)
```

---

### 3.4 State & Error Registers

| Address | Name | Type | Access | Scale | Invalid Marker | Description |
|---------|------|------|--------|-------|----------------|-------------|
| 0x001D | States | u8 (LSB) | RO | - | - | Burner and circuit state flags |
| 0x001E | Main Error | u16 | RO | - | 0xFFFF | Primary boiler error code |
| 0x001F | Additional Error | u16 | RO | - | 0xFFFF | Secondary error code |
| 0x0023 | OT Error Flags | s8 (MSB) | RO | - | 0x7F | OpenTherm-specific error flags |

#### Error Code Interpretation

Error codes are manufacturer-specific. Common patterns:
- `0x0000` = No error
- Other values = Manufacturer-specific error codes

#### Register 0x0023: OpenTherm Error Flags

**Only applicable for OpenTherm adapter type (bitfield 0x0010 = 000)**

This register contains OpenTherm protocol-specific error flags. The meaning of bits depends on the boiler manufacturer's implementation.

**Invalid marker:** `0x7F` = Error flags not available or not supported

---

### 3.5 Device Identification Registers

| Address | Name | Type | Access | Invalid Marker | Description |
|---------|------|------|--------|----------------|-------------|
| 0x0021 | Manufacturer Code | u16 | RO | 0xFFFF | Boiler manufacturer identifier |
| 0x0022 | Model Code | u16 | RO | 0xFFFF | Boiler model identifier |

---

### 3.6 Setpoint Control Registers

| Address | Name | Type | Access | Range | Description |
|---------|------|------|--------|-------|-------------|
| 0x0030 | External Connection Type | u8 | WO | 0-1 | External connection mode (saved to EPROM) |
| 0x0031 | CH Setpoint | i16 | WO | 0-1000 | Central heating target temperature (raw = temp × 10) |
| 0x0032 | Emergency CH Setpoint | i16 | WO | 0-1000 | Emergency CH temperature |
| 0x0033 | CH Min Limit | u8 | R/W | 0-100 | CH minimum allowed temperature |
| 0x0034 | CH Max Limit | u8 | R/W | 0-100 | CH maximum allowed temperature |
| 0x0035 | DHW Min Limit | u8 | R/W | 0-100 | DHW minimum allowed temperature |
| 0x0036 | DHW Max Limit | u8 | R/W | 0-100 | DHW maximum allowed temperature |
| 0x0037 | DHW Setpoint | u8 | WO | 0-100 | Domestic hot water target temperature (°C) |
| 0x0038 | Max Modulation | u8 | R/W | 0-100 | Maximum burner modulation level |

#### Register 0x0030: External Connection Type

**Important:** This register configures how the adapter connects to the boiler and is saved to EPROM (persistent storage).

```
Values:
  0 = Adapter connected directly to boiler
  1 = Boiler connected to external device (control panel or jumper)
```

**Impact:**
- Mode 0: Adapter acts as master on boiler interface
- Mode 1: Adapter acts as slave, external panel is master

**Note:** This should be configured during initial setup. Many boilers require raising the max temperature on the boiler panel before connecting the adapter to ensure proper temperature range negotiation.

#### Setpoint Write Examples

```
CH Setpoint (0x0031):
    Target: 45.0°C → Write 450  (45.0 × 10)
    Target: 60.5°C → Write 605  (60.5 × 10)

DHW Setpoint (0x0037):
    Target: 50°C → Write 50
    Target: 55°C → Write 55
```

---

### 3.7 Circuit Control Registers

| Address | Name | Type | Access | Description |
|---------|------|------|--------|-------------|
| 0x0039 | Circuit Enable | u16 | R/W | Circuit enable bitfield |

---

### 3.8 Command Registers

| Address | Name | Type | Access | Description |
|---------|------|------|--------|-------------|
| 0x0080 | Command | u16 | WO | Adapter command register |
| 0x0081 | Command Result | i16 | RO | Command execution result with detailed error codes |

---

### 3.9 Register Health Monitoring

**Address Range:** 0x0040 to 0x006F (48 registers)
**Type:** i16
**Access:** RO

These registers provide health and status information for registers 0x0010-0x003F. Each status register corresponds to a data register at address `status_addr - 0x30`.

#### Status Register Values

| Value | Meaning | Description |
|-------|---------|-------------|
| **-2** | Read/Write Error | Communication error with boiler for this register |
| **-1** | Not Supported | Register not supported by boiler model |
| **0** | Valid/ Accepted | Data is valid (read) or accepted by boiler (write) |
| **1** | Not Initialized | No data read yet or no write value set |

#### Detailed Status Descriptions

**Status = -2 (Read/Write Error)**
- Communication with boiler failed for this specific register
- May indicate wiring issue, boiler offline, or protocol error
- Retry operation may succeed

**Status = -1 (Not Supported)**
- Boiler does not support this register/function
- Feature not available on this boiler model
- Do not attempt to use this register

**Status = 0 (Valid/Accepted)**
- **For read registers:** Data successfully read from boiler and is valid
- **For write registers:** Value successfully accepted by boiler
- Normal operating state

**Status = 1 (Not Initialized)**
- **For read registers:** Adapter hasn't read this register from boiler yet (normal after startup)
- **For write registers:** No value has been set for writing to boiler
- Will change to 0 after first successful operation

#### Usage Example

To check the health of register 0x0018 (CH Temperature):
```python
# Read status for CH temperature register
status_addr = 0x0018 + 0x30  # 0x0048
status = await read_registers(slave_id, status_addr, 1)

if status[0] == -1:
    _LOGGER.warning("CH temperature not supported by boiler")
    return None
elif status[0] == -2:
    _LOGGER.error("Communication error reading CH temperature")
    return None
elif status[0] == 1:
    _LOGGER.debug("CH temperature not yet initialized")
    return None
# status[0] == 0: Data is valid, proceed with reading
```

#### Benefits

- **Feature Detection:** Determine which boiler features are actually supported
- **Error Isolation:** Identify specific registers with communication issues
- **Better UI:** Show "unsupported" vs "error" vs "unavailable" states
- **Debugging:** Pinpoint problematic registers during troubleshooting

---

### 3.10 Contact Sensor Splitter Registers

**Device Type:** 0x59 (10-channel Contact Sensor Splitter)

**Register Structure:** Bitfield-based channel states

**Description:**
The Contact Sensor Splitter is a device that monitors up to 10 independent contact inputs (door/window sensors, motion detectors, etc.) and reports their states via Modbus. Each channel can be in one of two states: closed (contact made) or open (contact broken).

#### Register Map

| Address | Name | Type | Access | Description |
|---------|------|------|--------|-------------|
| 0x0010 | Channels 1-8 | u16 | RO | Bitfield for channels 1-8 |
| 0x0011 | Channels 9-10 | u16 | RO | Bitfield for channels 9-10 |

#### Bitfield Structure

**Register 0x0010: Channels 1-8**

| Bit | Channel | Description |
|-----|---------|-------------|
| 0 | Channel 1 | 0 = Open, 1 = Closed |
| 1 | Channel 2 | 0 = Open, 1 = Closed |
| 2 | Channel 3 | 0 = Open, 1 = Closed |
| 3 | Channel 4 | 0 = Open, 1 = Closed |
| 4 | Channel 5 | 0 = Open, 1 = Closed |
| 5 | Channel 6 | 0 = Open, 1 = Closed |
| 6 | Channel 7 | 0 = Open, 1 = Closed |
| 7 | Channel 8 | 0 = Open, 1 = Closed |

**Register 0x0011: Channels 9-10**

| Bit | Channel | Description |
|-----|---------|-------------|
| 0 | Channel 9 | 0 = Open, 1 = Closed |
| 1 | Channel 10 | 0 = Open, 1 = Closed |

#### Dynamic Polling

The number of registers to read depends on the device's channel count:

```python
if channel_count <= 8:
    # Read only register 0x0010
    regs = await protocol.read_registers(slave_id, 0x0010, 1)
else:
    # Read both registers 0x0010-0x0011
    regs = await protocol.read_registers(slave_id, 0x0010, 2)
```

#### Bit Extraction Examples

**Extract Channel 1 state:**
```python
reg_0x0010 = 0x0005  # Binary: 0000000000000101
channel_1_state = (reg_0x0010 >> 0) & 0x01  # = 1 (Closed)
channel_2_state = (reg_0x0010 >> 1) & 0x01  # = 0 (Open)
channel_3_state = (reg_0x0010 >> 2) & 0x01  # = 1 (Closed)
```

**Extract Channel 9 state:**
```python
reg_0x0011 = 0x0003  # Binary: 0000000000000011
channel_9_state = (reg_0x0011 >> 0) & 0x01  # = 1 (Closed)
channel_10_state = (reg_0x0011 >> 1) & 0x01  # = 1 (Closed)
```

#### Reading Algorithm

```python
def get_channel_state(channel, channel_count, cache):
    """Get the state of a specific channel."""
    
    # Validate channel number
    if channel < 1 or channel > 10:
        raise ValueError("Channel must be 1-10")
    
    # Check if channel exists on this device
    if channel > channel_count:
        return None
    
    if channel <= 8:
        # Extract from register 0x0010
        reg_0x0010 = cache.get(0x0010)
        if reg_0x0010 is None:
            return None
        bit_position = channel - 1
        return bool((reg_0x0010 >> bit_position) & 0x01)
    else:
        # Extract from register 0x0011
        reg_0x0011 = cache.get(0x0011)
        if reg_0x0011 is None:
            return None
        bit_position = channel - 9  # Channel 9 = bit 0, Channel 10 = bit 1
        return bool((reg_0x0011 >> bit_position) & 0x01)
```

#### State Examples

**All channels closed:**
```
Register 0x0010: 0x00FF  (Binary: 0000000011111111) - Channels 1-8 closed
Register 0x0011: 0x0003  (Binary: 0000000000000011) - Channels 9-10 closed
```

**Alternating pattern:**
```
Register 0x0010: 0x0055  (Binary: 0000000001010101) - Channels 1,3,5,7 closed
Register 0x0011: 0x0001  (Binary: 0000000000000001) - Channel 9 closed
```

**All channels open:**
```
Register 0x0010: 0x0000  (Binary: 0000000000000000) - All channels 1-8 open
Register 0x0011: 0x0000  (Binary: 0000000000000000) - All channels 9-10 open
```

#### Device Configuration

**Channel Count:** Determined from register 0x0003 LSB (1-10 channels)

**Device Type:** 0x59 (Contact Sensor Splitter)

**UID Range:** 0x800000 - 0xFFFFFF (24-bit unique identifier)

#### Usage Notes

1. **Efficient Polling:** Only read register 0x0011 if device has >8 channels
2. **Bit Operations:** Use bitwise AND and shift operations for reliable bit extraction
3. **Cache Updates:** Update cache with both registers on each poll
4. **Channel Validation:** Always check channel count before accessing channels 9-10

#### Entity Mapping (Home Assistant)

Each channel should be exposed as a binary sensor entity:

- **Entity Type:** `binary_sensor`
- **Device Class:** `opening` (for door/window sensors)
- **Unique ID:** `ectocontrol_uid_{uid_hex}_channel_{n}`
- **State Mapping:**
  - `1` (Closed) → `on` (door/window closed)
  - `0` (Open) → `off` (door/window open)

---

### 3.11 Relay Control Devices

**Device Types:**
- 0xC0: 2-channel Relay Control Block
- 0xC1: 10-channel Relay Control Block (EctoRelay10CH)

**Description:**
Relay control devices allow external systems to control relay outputs via Modbus. The integration acts as a Modbus server, exposing relay states and timer configurations through holding registers.

#### Register Map (10-Channel Relay, Type 0xC1)

| Address | Name | Type | Access | Description |
|---------|------|------|--------|-------------|
| 0x0000-0x0003 | Device Info | u16×4 | RO | Standard device identification |
| 0x0010 | Channel States | u16 | R/W | Bitfield for channels 0-9 |
| 0x0020-0x0029 | Timer Registers | u16×10 | R/W | Per-channel timer configuration |

#### State Register (0x0010) - Bitfield Structure

The state register uses a 16-bit bitfield to represent the state of all 10 channels:

```
+--------+--------+--------+--------+--------+--------+--------+--------+
| Bit 15 | Bit 14 | Bit 13 | Bit 12 | Bit 11 | Bit 10 | Bit 9  | Bit 8  |
+--------+--------+--------+--------+--------+--------+--------+--------+
|  Ch 7  |  Ch 6  |  Ch 5  |  Ch 4  |  Ch 3  |  Ch 2  |  Ch 1  |  Ch 0  |
+--------+--------+--------+--------+--------+--------+--------+--------+
| MSB Byte (channels 0-7)                                                |
+--------+--------+--------+--------+--------+--------+--------+--------+
| Bit 7  | Bit 6  | Bit 5  | Bit 4  | Bit 3  | Bit 2  | Bit 1  | Bit 0  |
+--------+--------+--------+--------+--------+--------+--------+--------+
|  Resv  |  Resv  |  Resv  |  Resv  |  Resv  |  Resv  |  Ch 9  |  Ch 8  |
+--------+--------+--------+--------+--------+--------+--------+--------+
| LSB Byte (channels 8-9, bits 0-1 only)                                 |
+------------------------------------------------------------------------+
```

**Bit Mapping Formula:**
```
For channels 0-7:
  BYTE_NO = 0  (MSB byte)
  BIT_NO = 7 - channel

For channels 8-9:
  BYTE_NO = 1  (LSB byte)
  BIT_NO = channel - 8
```

**State Values:**
- `0` = Relay OFF (open)
- `1` = Relay ON (closed)

#### Timer Registers (0x0020-0x0029)

Each channel has a dedicated 16-bit timer register:

| Register | Channel | Description |
|----------|---------|-------------|
| 0x0020 | Channel 0 | Timer configuration |
| 0x0021 | Channel 1 | Timer configuration |
| ... | ... | ... |
| 0x0029 | Channel 9 | Timer configuration |

**Timer Register Format:**
```
+--------+--------+--------+--------+--------+--------+--------+--------+
| Bit 15 | Bit 14 | Bit 13 | Bit 12 | Bit 11 | Bit 10 | Bit 9  | Bit 8  |
+--------+--------+--------+--------+--------+--------+--------+--------+
| Init   | Timeout units (500ms each) - high byte                         |
+--------+--------+--------+--------+--------+--------+--------+--------+
| Bit 7  | Bit 6  | Bit 5  | Bit 4  | Bit 3  | Bit 2  | Bit 1  | Bit 0  |
+--------+--------+--------+--------+--------+--------+--------+--------+
| Timeout units (500ms each) - low byte                                  |
+------------------------------------------------------------------------+

Bit 15: Initial State
  0 = Relay starts OFF, turns ON after timeout
  1 = Relay starts ON, turns OFF after timeout

Bits 14-0: Timeout Value
  Timeout in units of 500ms (0-32767)
  Maximum timeout: 32767 × 500ms = 4.55 hours
```

**Timer Value Calculation:**
```python
# To set a timer:
timeout_seconds = 30  # 30 seconds
timeout_units = int(timeout_seconds * 2)  # Convert to 500ms units = 60
initial_state = True  # Start ON, turn OFF after timeout
timer_value = (1 << 15) if initial_state else 0  # Set bit 15 if initial ON
timer_value |= (timeout_units & 0x7FFF)  # Combine with timeout

# To read a timer:
initial_state = bool(timer_value & (1 << 15))
timeout_units = timer_value & 0x7FFF
timeout_seconds = timeout_units / 2.0
```

#### Example Transactions

**Set Channel 0 ON:**
```
Request:
  Function: 0x06 (Write Single Register)
  Slave ID: 5
  Address: 0x0010
  Value: 0x8000  # Channel 0 ON (bit 15 set)

Result: Relay channel 0 turns ON
```

**Set Channel 9 ON (all channels):**
```
Request:
  Function: 0x06 (Write Single Register)
  Slave ID: 5
  Address: 0x0010
  Value: 0x8003  # Ch 0 ON (bit 15) + Ch 8 ON (bit 0) + Ch 9 ON (bit 1)

Result: Channels 0, 8, 9 are ON
```

**Set Timer for Channel 0 (10 seconds, start ON):**
```
Request:
  Function: 0x06 (Write Single Register)
  Slave ID: 5
  Address: 0x0020
  Value: 0x8014  # Bit 15=1 (start ON), bits 14-0=20 (10s × 2)

Calculation:
  timeout_seconds = 10
  timeout_units = 10 × 2 = 20 (0x14)
  initial_state = True → bit 15 = 1
  timer_value = 0x8000 | 0x0014 = 0x8014

Result: Channel 0 turns ON immediately, then OFF after 10 seconds
```

**Read All Channel States:**
```
Request:
  Function: 0x03 (Read Holding Registers)
  Slave ID: 5
  Address: 0x0010
  Count: 1

Response:
  [0x8080]  # Binary: 1000000010000000

Interpretation:
  Bit 15 (Ch 7): 1 → Channel 7 ON
  Bit 8  (Ch 0): 1 → Channel 0 ON
  All other bits: 0 → OFF
```

**Read Timer Configuration:**
```
Request:
  Function: 0x03 (Read Holding Registers)
  Slave ID: 5
  Address: 0x0020
  Count: 10

Response:
  [0x8014, 0x0000, 0x0000, ...]  # Timer for channel 0 set, others 0

Interpretation:
  Channel 0: 0x8014 = initial ON, 10 second timeout
  Channels 1-9: 0x0000 = no timer configured
```

#### State Encoding Examples

| Channels ON | Register Value | Binary |
|-------------|----------------|--------|
| None | 0x0000 | 0000000000000000 |
| Ch 0 | 0x8000 | 1000000000000000 |
| Ch 7 | 0x0100 | 0000000100000000 |
| Ch 8 | 0x0001 | 0000000000000001 |
| Ch 9 | 0x0002 | 0000000000000010 |
| All (0-9) | 0x8103 | 1000000100000011 |
| Ch 0, 5 | 0x8400 | 1000010000000000 |

#### Home Assistant Integration

The `EctoRelay10CH` class exposes each channel as a switch entity:

```yaml
# configuration.yaml
ecto_modbus:
  port: /dev/ttyUSB0
  port_type: rs485
  devices:
    - type: relay_10ch
      addr: 5
```

This creates 10 switch entities:
- `switch.device_5_ch1` (Channel 0)
- `switch.device_5_ch2` (Channel 1)
- ...
- `switch.device_5_ch10` (Channel 9)

#### Usage Notes

1. **State Persistence:** Switch states are restored on Home Assistant restart
2. **Concurrent Access:** All Modbus operations are serialized via RS-485 lock
3. **Timer Automation:** Use Home Assistant automations to call `set_timer()` via service
4. **Bit Reversal:** Channels 0-7 use reversed bit ordering (same as binary sensor)

---

## 4. Data Type Reference

### 4.1 Signed 16-bit Integer (i16)

**Used for:** CH temperature, CH setpoint active

**Interpretation:**
```
If raw_value < 0x8000:
    signed_value = raw_value
Else:
    signed_value = raw_value - 0x10000  # Two's complement
```

**Example:**
```
Raw 0xFFEC (65532) → -20
Raw 0x0014 (20)     → +20
```

### 4.2 Unsigned 16-bit Integer (u16)

**Used for:** DHW temperature, error codes, manufacturer/model codes

**Interpretation:** Direct value (0 to 65535)

### 4.3 MSB Extraction (8-bit value from 16-bit register)

**Used for:** Pressure, flow rate, modulation, outdoor temperature, version

**Formula:**
```
msb = (raw_value >> 8) & 0xFF
```

**Example:**
```
Raw 0x0C34 → MSB = 0x0C = 12
Raw 0xF812 → MSB = 0xF8 = 248 (or -8 if signed i8)
```

### 4.4 LSB Extraction (8-bit value from 16-bit register)

**Used for:** States, software version

**Formula:**
```
lsb = raw_value & 0xFF
```

**Example:**
```
Raw 0x0C34 → LSB = 0x34 = 52
Raw 0x0005 → LSB = 0x05 = 5
```

### 4.5 Bitfield Operations

**Set a bit:**
```
new_value = current_value | (1 << bit_position)
```

**Clear a bit:**
```
new_value = current_value & ~(1 << bit_position)
```

**Test a bit:**
```
is_set = bool(current_value & (1 << bit_position))
```

### 4.6 Scaling Formulas

| Operation | Formula | Example |
|-----------|---------|---------|
| Temperature (×10) | `raw / 10.0` | 291 → 29.1°C |
| High precision (×256) | `raw / 256.0` | 11520 → 45.0°C |
| Pressure (÷10) | `(raw >> 8) / 10.0` | 0x0C34 → 1.2 bar |
| Direct percentage | `raw >> 8` | 0x4B00 → 75% |

---

## 5. Invalid/Unsupported Value Markers

These special values indicate that a sensor is not available, not supported, or has encountered an error.

| Marker | Hex | Type | Used In | Meaning |
|--------|-----|------|---------|---------|
| **0x7FFF** | 32767 | i16 | CH temp, DHW temp, CH setpoint active | Sensor not available or error |
| **0xFFFF** | 65535 | u16 | Error codes, version, manufacturer/model | Invalid or unavailable |
| **0xFF** | 255 | u8 (LSB) | Pressure, flow, modulation | Sensor not available |
| **0x7F** | 127 | i8 (MSB) | Outdoor temperature | Invalid reading |

### Handling Invalid Values

When an invalid marker is detected:
1. **Return `None`** in application code
2. **Display "Unavailable"** in UI
3. **Do NOT attempt** to use the value for calculations

---

## 6. Bitfield Definitions

### 6.1 Register 0x0010: Status Register

```
+--------+--------+--------+--------+
| Bit 15 | 14-4   |   3    |  2-0   |
+--------+--------+--------+--------+
| Reboot |  Resvd | CommOK | Type   |
+--------+--------+--------+--------+

Bits 0-2: Adapter Type
    000 = Unknown
    001 = Type A
    010 = Type B
    011 = Type C
    100-111 = Reserved

Bit 3: Communication Status
    0 = Communication OK
    1 = Communication Error

Bits 4-14: Reserved (read as 0)

Bit 15: Reboot Code
    0 = Normal startup
    1 = Watchdog reset
    2-255 = Other reset codes
```

### 6.2 Register 0x001D: States Register (LSB)

```
+--------+--------+--------+--------+
|   7-3  |   2    |   1    |   0    |
+--------+--------+--------+--------+
|  Resvd | DHW En |Heat En | Burner |
+--------+--------+--------+--------+

Bit 0: Burner On
    0 = Burner Off
    1 = Burner On

Bit 1: Heating Enabled
    0 = Heating Circuit Disabled
    1 = Heating Circuit Enabled

Bit 2: DHW Enabled
    0 = Domestic Hot Water Disabled
    1 = Domestic Hot Water Enabled

Bits 3-7: Reserved (read as 0)
```

### 6.3 Register 0x0039: Circuit Enable Register

```
+--------+--------+--------+--------+
|  15-2  |   1    |   0    |
+--------+--------+--------+
|  Resvd | DHW En |Heat En |
+--------+--------+--------+

Bit 0: Heating Circuit Enable
    0 = Disable heating circuit
    1 = Enable heating circuit

Bit 1: DHW Circuit Enable
    0 = Disable DHW circuit
    1 = Enable DHW circuit

Bits 2-15: Reserved (write as 0)
```

**Note:** This register uses read-modify-write pattern to preserve other bits.

---

## 7. Command Codes

### Register 0x0080: Command Register

| Command | Value | Description |
|---------|-------|-------------|
| No Command | 0 | Clear command register (default state) |
| CH Water Filling | 1 | Reserved for future use |
| Reboot Adapter | 2 | Initiates adapter reboot |
| Reset Boiler Errors | 3 | Clears boiler error codes |
| 4-65525 | Reserved | Reserved for future commands |

**Note:** Writing any command (except 0) immediately changes the command result register (0x0081) to value 2 (processing).

### Register 0x0081: Command Result

This register provides detailed feedback on command execution.

| Value | Meaning | Description |
|-------|---------|-------------|
| **-32768 to -6** | Reserved | Reserved for future use |
| **-5** | Command Execution Error | Error occurred while executing command |
| **-4** | Not Supported by Boiler | Boiler does not support this command |
| **-3** | Device ID Not Supported | Boiler doesn't recognize the device ID |
| **-2** | Not Supported by Adapter | Adapter doesn't support this command |
| **-1** | Timeout | No response from boiler within timeout period |
| **0** | Success | Command executed successfully |
| **1** | No Command | No command has been issued (default) |
| **2** | Processing | Command is currently being processed |
| **3 to 32767** | Reserved | Reserved for future use |

**Note:** After adapter reboot without issuing commands, register reads as 1 (no command).

### Command Execution Flow

```
1. Write command code to register 0x0080
   → Command result register immediately changes to 2 (processing)

2. Adapter executes command and communicates with boiler

3. Poll register 0x0081 for result:
   - 2 = Still processing (wait and retry)
   - 0 = Success
   - Negative value = Error (see table above)

4. Result persists until next command is issued
```

### Example: Reboot with Error Handling

```python
async def reboot_adapter_with_confirmation(slave_id):
    # Send reboot command
    await write_register(slave_id, 0x0080, 2)

    # Wait for processing
    await asyncio.sleep(0.5)

    # Check result
    max_attempts = 10
    for attempt in range(max_attempts):
        result = await read_register(slave_id, 0x0081)

        if result == 0:
            _LOGGER.info("Reboot command successful")
            return True
        elif result == 2:
            _LOGGER.debug(f"Reboot processing... attempt {attempt + 1}")
            await asyncio.sleep(0.5)
            continue
        elif result == -4:
            _LOGGER.error("Reboot not supported by boiler")
            return False
        elif result == -1:
            _LOGGER.error("Reboot command timeout")
            return False
        else:
            _LOGGER.warning(f"Reboot command result: {result}")
            return False

    _LOGGER.error("Reboot processing timeout")
    return False
```

---

## 8. Communication Patterns

### 8.1 Batch Read Strategy

For optimal performance, read all sensor registers in a single operation:

```
Read Holding Registers (Function 0x03)
    Slave ID: <slave_id>
    Start Address: 0x0010
    Register Count: 23 (0x0010 to 0x0026)

Returns: [reg_0x0010, reg_0x0011, ..., reg_0x0026]
```

**Advantages:**
- Single round-trip on RS-485 bus
- Consistent snapshot of all sensors
- Reduces bus traffic

### 8.2 Write Operations

Individual register writes for control operations:

```
Write Single Register (Function 0x06)
    Slave ID: <slave_id>
    Register Address: <address>
    Value: <value>
```

### 8.3 Bitfield Write Pattern (Read-Modify-Write)

For circuit enable register (0x0039):

```
1. Read current value from 0x0039
2. Modify specific bit(s)
3. Write modified value back to 0x0039
```

**Example - Enable Heating:**
```python
# Read current state
current = await read_registers(slave_id, 0x0039, 1)  # e.g., returns [0x0002]

# Set bit 0 (heating enable)
new_value = current[0] | (1 << 0)  # 0x0002 | 0x0001 = 0x0003

# Write back
await write_register(slave_id, 0x0039, new_value)
```

### 8.4 Polling

**Recommended interval:** 15 seconds

**Pattern:**
```
Every 15 seconds:
    1. Batch read registers 0x0010-0x0026
    2. Update local cache
    3. Notify entities of changes
```

### 8.5 Concurrency Control

**Critical:** RS-485 is half-duplex - only one transaction at a time!

```
Lock Pattern:
    async with lock:
        # Perform Modbus operation
        result = await read_registers(...)
```

**Implementation:** Use `asyncio.Lock()` to serialize all Modbus operations.

---

## 9. Error Handling

### 9.1 Modbus Exception Codes

| Code | Name | Meaning |
|------|------|---------|
| 0x01 | Illegal Function | Function code not supported |
| 0x02 | Illegal Data Address | Register address out of range |
| 0x03 | Illegal Data Value | Value invalid for register |
| 0x04 | Slave Device Failure | Internal error in adapter |
| 0x05 | Acknowledge | Request accepted, processing |
| 0x06 | Slave Device Busy | Adapter busy, retry later |
| 0x0E | Gateway Path Unavailable | Gateway unavailable (if applicable) |
| 0x0F | Gateway Target Device Failed to Respond | Target not responding |

### 9.2 Timeout Handling

**Default timeout:** 2.0 seconds

**Behavior:**
- Read timeout → Return `None`
- Write timeout → Return `False`
- Log error with details
- Do not raise exceptions

### 9.3 Retry Strategy

**Recommended approach:**
```
On failure:
    1. Log error
    2. Increment failure counter
    3. If failure_count >= 3:
        - Mark device as unavailable
    4. On next success:
        - Reset failure counter
        - Mark device as available
```

### 9.4 Error Recovery

**Transient errors:**
- Timeout, CRC error, device busy
- Action: Retry with exponential backoff

**Persistent errors:**
- Illegal address, slave offline
- Action: Mark unavailable, notify user

**Invalid data:**
- Invalid marker (0x7FFF, 0xFF, etc.)
- Action: Return `None`, entity shows unavailable

---

## 10. Example Transactions

### 10.1 Reading CH Temperature

**Scenario:** Read current heating temperature

```
Request:
    Function: 0x03 (Read Holding Registers)
    Slave ID: 1
    Start Address: 0x0018
    Count: 1

Response:
    [291]  # Raw register value

Processing:
    raw = 291
    if raw == 0x7FFF: return None  # Not invalid
    if raw >= 0x8000: raw -= 0x10000  # Not negative
    temperature = 291 / 10.0 = 29.1°C

Result: 29.1°C
```

### 10.2 Reading Pressure

**Scenario:** Read system pressure

```
Request:
    Function: 0x03 (Read Holding Registers)
    Slave ID: 1
    Start Address: 0x001A
    Count: 1

Response:
    [0x0C34]  # Raw register value

Processing:
    raw = 0x0C34 = 3092
    msb = (3092 >> 8) & 0xFF = 0x0C = 12
    if msb == 0xFF: return None  # Not invalid
    pressure = 12 / 10.0 = 1.2 bar

Result: 1.2 bar
```

### 10.3 Setting DHW Setpoint

**Scenario:** Set domestic hot water to 50°C

```
Request:
    Function: 0x06 (Write Single Register)
    Slave ID: 1
    Address: 0x0037
    Value: 50

Response:
    Success/Failure

Processing:
    value = 50  # Direct, no scaling for DHW setpoint

Result: Write 50 to register 0x0037
```

### 10.4 Setting CH Setpoint

**Scenario:** Set heating to 45°C

```
Request:
    Function: 0x06 (Write Single Register)
    Slave ID: 1
    Address: 0x0031
    Value: 450  # 45.0 × 10

Response:
    Success/Failure

Processing:
    target_temp = 45.0
    raw_value = int(45.0 × 10) = 450

Result: Write 450 to register 0x0031
```

### 10.5 Enabling Heating Circuit

**Scenario:** Enable heating via circuit enable register

```
Step 1 - Read current state:
    Request:  Function 0x03, Address 0x0039, Count 1
    Response: [0x0002]  # Only DHW enabled (bit 1)

Step 2 - Modify value:
    current = 0x0002
    new_value = current | (1 << 0)  # Set bit 0
    new_value = 0x0002 | 0x0001 = 0x0003

Step 3 - Write new state:
    Request:  Function 0x06, Address 0x0039, Value 0x0003
    Response: Success/Failure

Result: Both heating and DHW enabled
```

### 10.6 Batch Read All Sensors

**Scenario:** Read all sensor registers efficiently

```
Request:
    Function: 0x03 (Read Holding Registers)
    Slave ID: 1
    Start Address: 0x0010
    Count: 23

Response:
    [reg_0x0010, reg_0x0011, reg_0x0012, ..., reg_0x0026]

Processing:
    Index 0 (0x0010): Status register
    Index 1 (0x0011): Version register
    Index 8 (0x0018): CH temperature
    Index 9 (0x0019): DHW temperature
    Index 10 (0x001A): Pressure
    Index 11 (0x001B): Flow rate
    Index 12 (0x001C): Modulation level
    Index 13 (0x001D): States
    Index 14 (0x001E): Main error
    Index 15 (0x001F): Additional error
    Index 16 (0x0020): Outdoor temperature
    Index 17 (0x0021): Manufacturer code
    Index 18 (0x0022): Model code
    Index 22 (0x0026): CH setpoint active

Result: Complete sensor snapshot in single transaction
```

### 10.7 Interpreting Invalid Values

**Scenario:** Sensor not available

```
Response for CH temperature:
    [0x7FFF]

Processing:
    raw = 0x7FFF
    if raw == 0x7FFF:
        return None  # Sensor not available

Result: None (entity shows "unavailable")
```

### 10.8 Rebooting Adapter

**Scenario:** Send reboot command

```
Request:
    Function: 0x06 (Write Single Register)
    Slave ID: 1
    Address: 0x0080
    Value: 2  # Reboot command

Response:
    Success/Failure

Result: Adapter initiates reboot sequence
```

---

## 11. Implementation Notes

### 11.1 Async Wrapper Requirements

**Critical:** Modbus operations are blocking and must be wrapped for async compatibility:

```python
import asyncio

# WRONG - Blocks the event loop
result = client.execute(slave_id, function, addr, count)

# CORRECT - Use executor
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(
    None,
    client.execute,
    slave_id,
    function,
    addr,
    count
)
```

### 11.2 Lock Pattern for Half-Duplex

**Critical:** RS-485 half-duplex requires serialized operations:

```python
class ModbusProtocol:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def read_registers(self, slave_id, addr, count):
        async with self._lock:  # Serialize access
            # Perform Modbus operation
            result = await self._execute_read(...)
            return result
```

### 11.3 Cache Strategy

**Recommended approach:**
```
1. Coordinator polls registers every 15 seconds
2. Store raw values in gateway.cache dict
3. Entities read from cache via gateway getters
4. Gateway getters apply scaling and return converted values
```

**Benefits:**
- Entities never block on Modbus operations
- Consistent state across entities
- Reduced bus traffic

### 11.4 Error Handling Pattern

```python
async def read_registers(self, slave_id, addr, count):
    try:
        # ... Modbus operation ...
        return result
    except modbus.ModbusError as exc:
        _LOGGER.error("Modbus error: %s", exc)
        return None  # Return None on error
    except Exception as exc:
        _LOGGER.error("Unexpected error: %s", exc)
        return None  # Return None on error
```

**Do NOT raise exceptions** from protocol layer - return `None`/`False` instead.

### 11.5 Signed Integer Handling

**Python doesn't have signed 16-bit integers** - use this pattern:

```python
# For i16 values that may be negative
if raw >= 0x8000:
    raw = raw - 0x10000  # Convert to signed

# For i8 values (MSB extraction)
msb = (raw >> 8) & 0xFF
if msb >= 0x80:
    msb = msb - 0x100  # Convert to signed
```

### 11.6 Testing Recommendations

**Use fake objects for testing, not mocks:**

```python
class FakeGateway:
    def __init__(self):
        self.cache = {REGISTER_CH_TEMP: 291}

    def get_ch_temperature(self):
        raw = self.cache.get(REGISTER_CH_TEMP)
        if raw is None or raw == 0x7FFF:
            return None
        if raw >= 0x8000:
            raw = raw - 0x10000
        return raw / 10.0

# Test
gateway = FakeGateway()
assert gateway.get_ch_temperature() == 29.1
```

### 11.7 Performance Considerations

| Metric | Value |
|--------|-------|
| Typical round-trip time | 100-500 ms |
| Batch read size | 23 registers (recommended) |
| Polling interval | 15 seconds (default) |
| Memory per device | ~46 bytes (cache) |
| Maximum devices per port | 32 (slave ID range) |

### 11.8 Hardware Tips

1. **Termination:** Use 120Ω termination resistors at both ends of RS-485 bus
2. **Cabling:** Use twisted-pair cable with shielding
3. **Distance:** RS-485 can support up to 1200 meters at lower baud rates
4. **Grounding:** Proper grounding reduces noise and errors
5. **Bias:** Some installations may need bias resistors

---

## Appendix A: Register Quick Reference

| Address | Name | Type | Scale | Access |
|---------|------|------|-------|--------|
| 0x0010 | Status | u16 | - | RO |
| 0x0011 | Version | u16 | - | RO |
| 0x0012 | Uptime High | u16 | - | RO |
| 0x0013 | Uptime Low | u16 | - | RO |
| 0x0018 | CH Temperature | i16 | ÷10 | RO |
| 0x0019 | DHW Temperature | u16 | ÷10 | RO |
| 0x001A | Pressure | u8 MSB | ÷10 | RO |
| 0x001B | Flow Rate | u8 MSB | ÷10 | RO |
| 0x001C | Modulation | u8 MSB | 1 | RO |
| 0x001D | States | u8 LSB | - | RO |
| 0x001E | Main Error | u16 | - | RO |
| 0x001F | Additional Error | u16 | - | RO |
| 0x0020 | Outdoor Temp | i8 MSB | 1 | RO |
| 0x0021 | Manufacturer Code | u16 | - | RO |
| 0x0022 | Model Code | u16 | - | RO |
| 0x0023 | OT Error Flags | s8 MSB | - | RO |
| 0x0026 | CH Setpoint Active | i16 | ÷256 | RO |
| 0x0030 | External Connection Type | u8 | - | WO |
| 0x0031 | CH Setpoint | i16 | ×10 | WO |
| 0x0032 | Emergency CH | i16 | ×10 | WO |
| 0x0033 | CH Min Limit | u8 | - | R/W |
| 0x0034 | CH Max Limit | u8 | - | R/W |
| 0x0035 | DHW Min Limit | u8 | - | R/W |
| 0x0036 | DHW Max Limit | u8 | - | R/W |
| 0x0037 | DHW Setpoint | u8 | - | WO |
| 0x0038 | Max Modulation | u8 | - | R/W |
| 0x0039 | Circuit Enable | u16 | - | R/W |
| 0x0040-0x006F | Register Health | i16 | - | RO |
| 0x0080 | Command | u16 | - | WO |
| 0x0081 | Command Result | i16 | - | RO |

---

## Appendix B: Function Code Reference

| Code | Name | Description |
|------|------|-------------|
| 0x03 | Read Holding Registers | Read block of holding registers |
| 0x04 | Read Input Registers | Read block of input registers |
| 0x06 | Write Single Register | Write one holding register |
| 0x10 | Write Multiple Registers | Write block of holding registers |

---

**Document End**

For questions or updates to this protocol reference, please refer to the project repository or contact the maintainers.
