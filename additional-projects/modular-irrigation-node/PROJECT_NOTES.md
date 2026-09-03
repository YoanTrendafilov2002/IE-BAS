# Project Notes

This file records the prototype state, design choices, and next tasks.

## Current State

The project is at the electronics/prototype stage. The app/dashboard should wait until the hardware configuration is stable.

What is done:

- Electrical configuration selected.
- KiCad schematic generated and exported.
- Elimex/TU-store shopping list created.
- Wire-by-wire build instructions created.
- K2402 irrigation kit evaluated as a useful donor kit.

## Current Hardware Decision

Use this final node architecture:

```text
LiPo battery -> K548 charger -> main switch -> K585 boost -> 5 V rail
5 V rail -> ESP32 5V/VIN
5 V rail -> pump positive
pump negative -> MOSFET drain
MOSFET source -> GND
ESP32 GPIO5 -> 100 ohm -> MOSFET gate
MOSFET gate -> 10k -> GND
```

Sensors:

```text
BH1750: I2C on GPIO8 SDA / GPIO9 SCL, powered from 3.3 V
SHT30/SHT31: I2C on same bus, powered from 3.3 V
K2402 capacitive soil sensor: AO -> GPIO1 ADC, powered from 3.3 V
XSL-4510-P float switch: GPIO6 with 10k pull-up to 3.3 V, switch to GND
Battery divider: switched battery positive -> 100k -> GPIO2 ADC -> 100k -> GND
```

## Important Decisions

- Use K2402 as a donor kit for pumps, capacitive soil sensors, hose, breadboard, and jumper wires.
- Do not redesign around the UNO or relay board from K2402.
- Use IRLB3034 if IRLZ44N is unavailable.
- Do not use K010 liquid-level controller; it needs 10-16 V.
- Use XSL-4510-P passive float switch for tank level.

## Key Files To Read First

1. `electronics/wiring_list_explained.txt`
2. `bom/updated_elimex_tu_parts_list.txt`
3. `electronics/electronic_configuration_connections.py`
4. `kicad/plant_watering_controller.kicad_sch`

## Validation Already Done

KiCad CLI 10.0.3 ran ERC successfully:

```text
0 Errors
0 Warnings
```

## Next Tasks

1. Confirm the exact ESP32-S3 Zero board pin labels before soldering.
2. Bench-test only the power path first.
3. Adjust K585 to 5.0 V with a multimeter.
4. Test pump through MOSFET with short pulses.
5. Calibrate pump flow in mL/s.
6. Calibrate soil sensor wet/dry values.
7. Verify XSL-4510-P tank switch polarity after mounting.
8. Only then start firmware logic and app/dashboard work.

## Safety Rules

- Pump current must not pass through ESP32 GPIO.
- Never feed 5 V into ESP32 GPIO.
- All grounds must be common.
- Battery voltage is measured before the boost converter.
- Pump must be disabled if battery is low or tank is empty.
