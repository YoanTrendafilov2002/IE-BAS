# Basic ESP32-S3 watering schematic notes

This schematic uses the listed parts as a battery-powered plant/water controller:

- `K548` Li-ion/LiPo charger: USB-C charges the 3.7 V LiPo. Battery connects to `B+` and `B-`; load comes from `OUT+` and `OUT-`.
- Slide switch: in series with charger `OUT+` before the boost converter.
- `K585` boost converter: input from charger output; adjust `VOUT` to `5.0 V` before connecting the rest of the circuit.
- ESP32-S3-Zero: power its `5V` pin from the boost output and share `GND`. Use its `3V3` pin only for low-current sensor modules.
- I2C bus: `GPIO8 = SDA`, `GPIO9 = SCL`. Connect BH1750, SHT30/SHT31, or BME280 to the same bus.
- Soil moisture sensor: `VCC = 3V3`, `GND = GND`, analog output to `GPIO4`.
- Tank level switch: one side to `GPIO5`, one side to `GND`, with a `10 kohm` pull-up from `GPIO5` to `3V3`.
- Pump: pump positive to `+5 V`; pump negative to IRLB3034 drain. IRLB3034 source to `GND`.
- MOSFET gate: `GPIO12` through `100 ohm` to IRLB3034 gate; `10 kohm` from gate to `GND`.
- Flyback diode: `1N5819` across the pump, cathode to `+5 V`, anode to MOSFET drain/pump negative.
- Decoupling: place `470 uF / 16 V` across `+5 V` and `GND` near the pump; optionally add `100 nF` ceramic nearby.

Important assumptions:

- The tank level part is treated as a simple 2-wire float/contact sensor. If your K010 board is a powered relay/controller module instead, do not wire it directly like the float input; use its relay/contact output or provide its required supply separately.
- The BH1750 entries are duplicate light-sensor choices. Use one BH1750 by default. If you mount both, set one `ADDR` low and the other high so the I2C addresses do not collide.
- Use either SHT30/SHT31 or BME280 for environment sensing unless you intentionally want both. BME280 modules must be 3.3 V-safe on I2C.
- The pump current is listed as about 200 mA, so the MOSFET is oversized but fine. Keep pump current off the ESP32 `3V3` rail.

Files:

- `basic_watering_schematic.svg` is the visual schematic.
