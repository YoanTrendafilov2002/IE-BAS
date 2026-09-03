# Modular Irrigation Plant Node

This repository contains a diploma prototype for a battery-powered ESP32 plant irrigation and monitoring node.

The current design uses:

- ESP32-S3 Zero controller
- LiPo battery with K548 USB-C charger
- K585 boost converter set to 5.0 V
- MOSFET low-side pump driver
- K2402 donor kit for pump, capacitive soil sensor, hose, breadboard, and wires
- XSL-4510-P passive float switch for tank-low detection
- BH1750 light sensor
- SHT30/SHT31 air temperature/humidity sensor

## Start Here

Read [PROJECT_NOTES.md](PROJECT_NOTES.md) first for the current design decisions, completed work, and next tasks.

## Key Files

- [electronics/wiring_list_explained.txt](electronics/wiring_list_explained.txt) - wire-by-wire build instructions.
- [bom/updated_elimex_tu_parts_list.txt](bom/updated_elimex_tu_parts_list.txt) - latest practical Elimex/TU-store shopping list.
- [electronics/electronic_configuration_connections.py](electronics/electronic_configuration_connections.py) - machine-readable net model.
- [kicad/plant_watering_controller.kicad_sch](kicad/plant_watering_controller.kicad_sch) - KiCad schematic.
- [kicad/plant_watering_controller.pdf](kicad/plant_watering_controller.pdf) - schematic PDF export.
- [kicad/plant_watering_controller_preview.png](kicad/plant_watering_controller_preview.png) - schematic preview.

## Regenerate KiCad Outputs

KiCad CLI 10 was used:

```powershell
python scripts\rewrite_direct_kicad.py
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' sch erc --severity-all --output 'kicad\plant_watering_controller_erc.rpt' 'kicad\plant_watering_controller.kicad_sch'
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' sch export pdf --output 'kicad\plant_watering_controller.pdf' 'kicad\plant_watering_controller.kicad_sch'
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' sch export svg --output 'kicad\plant_watering_controller_svg' 'kicad\plant_watering_controller.kicad_sch'
```

The last recorded ERC result was 0 errors and 0 warnings.

## Important Electrical Notes

- Set K585 output to exactly 5.0 V before connecting ESP32 or pump.
- Do not use K010 in the final node; it requires 10-16 V.
- Use XSL-4510-P for tank level instead.
- Use MOSFET switching, not the K2402 relay module, for the final battery node.
- Never put 5 V directly into ESP32 GPIO.
- All grounds must be common.
