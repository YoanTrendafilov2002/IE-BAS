# Codex Project Notes

When opening this repository in Codex, start with `CODEX_START_HERE.md`.

The hardware configuration is intentionally conservative:

- ESP32 + LiPo + charger + boost converter
- MOSFET pump driver
- 3.3 V sensors only on ESP32 GPIO/ADC/I2C
- XSL-4510-P tank switch instead of K010
- K2402 as donor kit, not as the control architecture

Do not start app/dashboard work until the hardware bench tests pass.
