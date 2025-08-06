# Energy Meter Protocol Documentation (1-Phase)

This file describes the communication protocol for reading and writing data to a 1-phase digital energy meter via UART at 2400 baud.

---

## 📥 Read Command

- **Baud Rate**: 2400
- **Command to Send**: 0xCC 0x91 0xDD
- **Response**: 44 bytes of data

### 🧾 Data Format Breakdown

| Field                          | Size (bytes) | Decimal Places | Notes                             |
|-------------------------------|--------------|----------------|-----------------------------------|
| Instant Voltage               | 2            | 2              |                                   |
| Instant Current               | 2            | 3              |                                   |
| Instant Power Factor          | 1            | 2              | Unsigned                          |
| Instant Load (kW)             | 3            | 5              |                                   |
| Instant Load (kVA)            | 3            | 5              |                                   |
| Cumulative kWh (Total)        | 3            | 2              |                                   |
| Cumulative kWh (TOD-1)        | 3            | 2              |                                   |
| Cumulative kWh (TOD-2)        | 3            | 2              |                                   |
| Cumulative kWh (TOD-3)        | 3            | 2              |                                   |
| Cumulative kWh (TOD-4)        | 3            | 2              |                                   |
| Meter Serial Number           | 3            | —              |                                   |
| Date (DD)                     | 1            | —              | Day of the month                  |
| Month (MM)                    | 1            | —              |                                   |
| Year (YY)                     | 1            | —              |                                   |
| Hour                          | 1            | —              | 24-hour format                    |
| Minute                        | 1            | —              |                                   |
| Second                        | 1            | —              |                                   |
| Frequency                     | 2            | 1              | Hz                                |
| Reverse Tamper Flag           | 1            | —              |                                   |
| Earth Tamper Flag             | 1            | —              |                                   |
| NM Tamper Flag                | 1            | —              |                                   |
| ND Tamper Flag                | 1            | —              |                                   |
| Magnet Tamper Flag            | 1            | —              |                                   |
| Cover Open Tamper Flag        | 1            | —              |                                   |
| End Byte                      | 1            | —              | Always `0xDD`                     |

---

## ⏲️ Set Date & Time Command

To set the real-time clock (RTC) on the energy meter, send the following format:

### Example Command:
CC 02 07 1E 05 07 0B 0F DD


### Breakdown:

| Bytes         | Meaning           | Example | Description              |
|---------------|-------------------|---------|--------------------------|
| `CC 02`       | Header            | —       | Fixed prefix             |
| `07 1E 05`    | Time              | 07:30:05| Hour, Minute, Second     |
| `07 0B 0F`    | Date              | 07/11/15| Day, Month, Year         |
| `DD`          | End Byte          | —       | Terminator byte          |

---

## 📝 Notes

- All values are sent in **raw binary** format (not ASCII).
- You must handle **decimal point placement** manually in your code.
- Be careful of **endianness** when decoding multi-byte values.
- This protocol is used with a 1-phase meter connected to a microcontroller (e.g. ATmega328PB) and a SIMCOM GPRS module.

---

**Maintainer:** [Rhythm Kachhwaha](https://github.com/Rhythm-Kachhwaha)  
**Project:** [IoT-based Live Carbon Emission Monitoring](https://github.com/Rhythm-Kachhwaha/Iot-based-Live-Carbon-emission-Monitoring)

