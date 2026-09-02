# KiCad project: plant watering controller

Open `plant_watering_controller.kicad_pro` in KiCad 10, then open the schematic.

This is a module-level schematic for the purchased boards and parts, not a PCB layout. It shows the fitted wiring only: charger, LiPo, switch, boost converter, ESP32-S3-Zero, one BH1750 light sensor, one SHT30/SHT31 temperature/humidity sensor, soil sensor, tank level switch, and MOSFET pump driver.

Important wiring notes:

- Adjust the K585/MT3608 boost converter to `5.0 V` before connecting the ESP32-S3-Zero and pump.
- Use the ESP32 `3V3` pin only for sensor modules, not for the pump.
- Keep the pump on the boosted `+5V` rail and switch its low side through the IRLB3034.
- Put the `1N5819` flyback diode across the pump: cathode to `+5V`, anode to `PUMP_DRAIN`.
- Put the `470 uF / 16 V` capacitor near the pump supply.
- The tank input assumes a simple 2-wire float/contact sensor. If the K010 board is used as an active controller/relay board, use its dry contact output or match its supply requirements instead.
- The BH1750 `ADDR` pin is wired to `GND`, giving the usual `0x23` I2C address.
