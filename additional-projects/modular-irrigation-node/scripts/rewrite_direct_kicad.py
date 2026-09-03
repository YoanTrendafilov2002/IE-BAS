from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "kicad"
SCH = OUT / "plant_watering_controller.kicad_sch"

src = SCH.read_text(encoding="ascii", errors="ignore")


def extract_form(text: str, start: int) -> tuple[str, int]:
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1], i + 1
    raise ValueError("unterminated form")


lib_start = src.index("\t(lib_symbols")
lib_symbols, _ = extract_form(src, lib_start)

uid_n = 400000


def uid() -> str:
    global uid_n
    uid_n += 1
    return f"33333333-3333-4333-8333-{uid_n:012d}"


def font(size: float = 1.27, hide: bool = False, bold: bool = False) -> str:
    h = " (hide yes)" if hide else ""
    b = " (bold yes)" if bold else ""
    return f"(effects (font (size {size:g} {size:g}){b}){h})"


def sym_prop(name: str, value: str, x: float = 0, y: float = 0, hide: bool = False) -> str:
    return f'\t\t\t(property "{name}" "{value}" (at {x:g} {y:g} 0) {font(1.27, hide)})'


def pin(kind: str, shape: str, x: float, y: float, rot: int, name: str, num: str) -> str:
    return (
        f'\t\t\t\t(pin {kind} {shape} (at {x:g} {y:g} {rot}) (length 5.08) '
        f'(name "{name}" {font()}) (number "{num}" {font()}))'
    )


def direct_symbols() -> str:
    return r'''
		(symbol "PlantWatering:ESP32_S3_ZERO_DIRECT"
			(pin_names (offset 1.016))
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(property "Reference" "U" (at 0 -36.83 0) (effects (font (size 1.27 1.27))))
			(property "Value" "ESP32_S3_ZERO_DIRECT" (at 0 36.83 0) (effects (font (size 1.27 1.27))))
			(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(property "Datasheet" "https://www.waveshare.com/wiki/ESP32-S3-Zero" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(property "Description" "ESP32-S3-Zero pins grouped by connected circuit for clean direct wiring" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(symbol "ESP32_S3_ZERO_DIRECT_0_1"
				(rectangle (start -17.78 -33.02) (end 17.78 53.34) (stroke (width 0) (type default)) (fill (type none)))
				(text "ESP32-S3" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
				(text "Zero" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
			)
			(symbol "ESP32_S3_ZERO_DIRECT_1_1"
				(pin passive line (at -22.86 48.26 0) (length 5.08) (name "5V" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
				(pin passive line (at -22.86 5.08 0) (length 5.08) (name "GPIO1_SOIL_ADC" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
				(pin passive line (at -22.86 -15.24 0) (length 5.08) (name "GPIO6_LEVEL" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
				(pin passive line (at -22.86 -25.4 0) (length 5.08) (name "GPIO5_PUMP" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
				(pin passive line (at 22.86 30.48 180) (length 5.08) (name "3V3" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
				(pin passive line (at 22.86 25.4 180) (length 5.08) (name "GND" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
				(pin passive line (at 22.86 20.32 180) (length 5.08) (name "GPIO8_SDA" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
				(pin passive line (at 22.86 15.24 180) (length 5.08) (name "GPIO9_SCL" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
			)
			(embedded_fonts no)
		)
		(symbol "PlantWatering:I2C_4_LEFT_DIRECT"
			(pin_names (offset 1.016))
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(property "Reference" "J" (at 0 -12.7 0) (effects (font (size 1.27 1.27))))
			(property "Value" "I2C_4_LEFT_DIRECT" (at 0 12.7 0) (effects (font (size 1.27 1.27))))
			(property "Footprint" "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(property "Description" "Four-wire I2C module connector" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(symbol "I2C_4_LEFT_DIRECT_0_1"
				(rectangle (start -15.24 -10.16) (end 15.24 10.16) (stroke (width 0) (type default)) (fill (type none)))
				(text "I2C" (at 0 0 0) (effects (font (size 1.27 1.27))))
			)
			(symbol "I2C_4_LEFT_DIRECT_1_1"
				(pin passive line (at -20.32 7.62 0) (length 5.08) (name "VCC_3V3" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
				(pin passive line (at -20.32 2.54 0) (length 5.08) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
				(pin passive line (at -20.32 -2.54 0) (length 5.08) (name "SDA" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
				(pin passive line (at -20.32 -7.62 0) (length 5.08) (name "SCL" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
			)
			(embedded_fonts no)
		)
		(symbol "PlantWatering:Soil_Mixed_DIRECT"
			(pin_names (offset 1.016))
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(property "Reference" "J" (at 0 -12.7 0) (effects (font (size 1.27 1.27))))
			(property "Value" "Soil_Mixed_DIRECT" (at 0 12.7 0) (effects (font (size 1.27 1.27))))
			(property "Footprint" "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(property "Datasheet" "K2112 soil moisture module product page" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(property "Description" "Soil module connector arranged to avoid crossing wires" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(symbol "Soil_Mixed_DIRECT_0_1"
				(rectangle (start -12.7 -10.16) (end 12.7 10.16) (stroke (width 0) (type default)) (fill (type none)))
				(text "SOIL" (at 0 0 0) (effects (font (size 1.27 1.27))))
			)
			(symbol "Soil_Mixed_DIRECT_1_1"
				(pin passive line (at -17.78 10.16 0) (length 5.08) (name "VCC_3V3" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
				(pin passive line (at 17.78 0 180) (length 5.08) (name "AO" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
				(pin passive line (at -17.78 -10.16 0) (length 5.08) (name "GND" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
			)
			(embedded_fonts no)
		)
		(symbol "PlantWatering:Level_Mixed_DIRECT"
			(pin_names (offset 1.016))
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(property "Reference" "J" (at 0 -10.16 0) (effects (font (size 1.27 1.27))))
			(property "Value" "Level_Mixed_DIRECT" (at 0 10.16 0) (effects (font (size 1.27 1.27))))
			(property "Footprint" "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(property "Datasheet" "https://elimex.bg/product/91654-datchik-za-nivo-xsl-4510-p" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(property "Description" "XSL-4510-P passive tank float switch connector arranged to avoid crossing wires" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
			(symbol "Level_Mixed_DIRECT_0_1"
				(rectangle (start -12.7 -7.62) (end 12.7 7.62) (stroke (width 0) (type default)) (fill (type none)))
				(text "LEVEL" (at 0 0 0) (effects (font (size 1.27 1.27))))
			)
			(symbol "Level_Mixed_DIRECT_1_1"
				(pin passive line (at 17.78 5.08 180) (length 5.08) (name "SW" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
				(pin passive line (at -17.78 -5.08 0) (length 5.08) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
			)
			(embedded_fonts no)
		)
'''


for name in (
    "Level_2_Right",
    "ESP32_S3_ZERO_DIRECT",
    "I2C_4_LEFT_DIRECT",
    "Soil_Mixed_DIRECT",
    "Level_Mixed_DIRECT",
):
    needle = f'\n\t\t(symbol "PlantWatering:{name}"'
    while True:
        start = lib_symbols.find(needle)
        if start == -1:
            break
        _, end = extract_form(lib_symbols, start + 3)
        lib_symbols = lib_symbols[:start] + lib_symbols[end:]

lib_symbols = lib_symbols[:-2] + direct_symbols() + "\n\t)"
lib_symbols = lib_symbols.replace("MOSFET_IRLZ44N", "MOSFET_IRLB3034")
lib_symbols = lib_symbols.replace("IRLZ44N datasheet", "IRLB3034 datasheet")
lib_symbols = lib_symbols.replace('"IRLZ44N"', '"IRLB3034"')


def prop(name: str, value: str, x: float, y: float, hide: bool = False) -> str:
    h = " (hide yes)" if hide else ""
    return f'\t\t(property "{name}" "{value}" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)){h}))'


def inst(ref: str) -> str:
    return f'\t\t(instances (project "plant_watering_controller" (path "/33333333-3333-4333-8333-333333333333" (reference "{ref}") (unit 1))))'


def place(lib_id: str, ref: str, value: str, x: float, y: float, pins: int, footprint: str = "", datasheet: str = "", desc: str = "") -> str:
    pin_lines = "\n".join(f'\t\t(pin "{i}" (uuid "{uid()}"))' for i in range(1, pins + 1))
    return f'''\
\t(symbol (lib_id "PlantWatering:{lib_id}") (at {x:g} {y:g} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", ref, x, y - 12.7)}
{prop("Value", value, x, y + 12.7)}
{prop("Footprint", footprint, x, y, True)}
{prop("Datasheet", datasheet, x, y, True)}
{prop("Description", desc, x, y, True)}
{pin_lines}
{inst(ref)}
\t)'''


def wire(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'\t(wire (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g})) (stroke (width 0) (type solid)) (uuid "{uid()}"))'


def polywire(points: list[tuple[float, float]]) -> str:
    pts = " ".join(f"(xy {x:g} {y:g})" for x, y in points)
    return f'\t(wire (pts {pts}) (stroke (width 0) (type solid)) (uuid "{uid()}"))'


def junction(x: float, y: float) -> str:
    return f'\t(junction (at {x:g} {y:g}) (diameter 1.016) (color 0 0 0 0) (uuid "{uid()}"))'


def text(s: str, x: float, y: float, size: float = 1.27, bold: bool = False) -> str:
    b = " (bold yes)" if bold else ""
    return f'\t(text "{s}" (exclude_from_sim no) (at {x:g} {y:g} 0) (effects (font (size {size:g} {size:g}){b}) (justify left bottom)) (uuid "{uid()}"))'


items: list[str] = [
    text("Direct-wired schematic", 20.32, 25.4, 1.8, True),
    text("Power", 20.32, 35.56, 1.6, True),
    text("Sensors and ESP32", 20.32, 93.98, 1.6, True),
    text("Pump driver", 205.74, 203.2, 1.6, True),
]

items += [
    place("Battery_2_Right", "BT1", "LiPo", 35.56, 68.58, 2, datasheet="https://www.ardboard.com/li-po-103450-3.7v-2000mah-jst-battery"),
    place("Charger_K548", "U1", "USB-C charger", 83.82, 68.58, 4, datasheet="K548 / TP4056-style charger module"),
    place("Switch_Inline", "SW1", "Switch", 119.38, 66.04, 2),
    place("Boost_K585", "U2", "5V boost", 157.48, 68.58, 4, datasheet="MT3608-style boost converter module"),
    place("ESP32_S3_ZERO_DIRECT", "U3", "ESP32-S3-Zero", 165.1, 139.7, 8, datasheet="https://www.waveshare.com/wiki/ESP32-S3-Zero"),
    place("I2C_4_LEFT_DIRECT", "J1", "BH1750", 320.04, 116.84, 4, footprint="Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", datasheet="ROHM BH1750FVI datasheet", desc="4-wire connection shown; ADDR left at module default/low address wiring"),
    place("I2C_4_LEFT_DIRECT", "J2", "SHT31", 391.16, 116.84, 4, footprint="Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", datasheet="Sensirion SHT3x-DIS datasheet"),
    place("Soil_Mixed_DIRECT", "J3", "Soil", 63.5, 127.0, 3, footprint="Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical"),
    place("Level_Mixed_DIRECT", "J4", "XSL-4510-P", 63.5, 180.34, 2, footprint="Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", datasheet="https://elimex.bg/product/91654-datchik-za-nivo-xsl-4510-p", desc="Passive NC float switch; verify wet/dry polarity after mounting."),
    place("Part_2_V", "R3", "10k", 76.2, 154.94, 2, footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"),
    place("Pump_2_Right", "J5", "Pump", 246.38, 226.06, 2, footprint="Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    place("Part_2_V", "D1", "1N5819", 302.26, 226.06, 2, footprint="Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal"),
    place("Part_2_H", "R1", "100R", 309.88, 241.3, 2, footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"),
    place("Part_2_V", "R2", "10k", 322.58, 259.08, 2, footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"),
    place("MOSFET_IRLB3034", "Q1", "IRLB3034", 342.9, 241.3, 3, footprint="Package_TO_SOT_THT:TO-220-3_Vertical"),
    place("Part_2_V", "C1", "470uF", 388.62, 259.08, 2, footprint="Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"),
]

# Power chain.
items += [
    wire(53.34, 66.04, 63.5, 66.04),
    wire(53.34, 71.12, 63.5, 71.12),
    wire(104.14, 66.04, 109.22, 66.04),
    wire(129.54, 66.04, 137.16, 66.04),
    wire(104.14, 71.12, 137.16, 71.12),
]

# +5V direct branches from boost output.
items += [
    wire(177.8, 66.04, 416.56, 66.04),
    wire(190.5, 66.04, 190.5, 83.82),
    wire(190.5, 83.82, 132.08, 83.82),
    wire(132.08, 83.82, 132.08, 91.44),
    wire(132.08, 91.44, 142.24, 91.44),
    wire(416.56, 66.04, 416.56, 220.98),
    wire(416.56, 220.98, 264.16, 220.98),
    junction(190.5, 66.04),
    junction(132.08, 91.44),
    text("+5V", 194.31, 64.77),
]

# Ground direct returns from boost to sensors and pump.
items += [
    wire(35.56, 71.12, 53.34, 71.12),
    wire(137.16, 71.12, 177.8, 71.12),
    wire(35.56, 71.12, 35.56, 274.32),
    wire(35.56, 274.32, 388.62, 274.32),
    wire(187.96, 114.3, 134.62, 114.3),
    wire(134.62, 114.3, 134.62, 119.38),
    wire(134.62, 119.38, 53.34, 119.38),
    wire(53.34, 119.38, 53.34, 137.16),
    wire(53.34, 137.16, 53.34, 152.4),
    wire(53.34, 152.4, 45.72, 152.4),
    wire(187.96, 114.3, 299.72, 114.3),
    wire(299.72, 114.3, 370.84, 114.3),
    junction(35.56, 71.12),
    junction(35.56, 152.4),
    junction(35.56, 274.32),
    junction(137.16, 71.12),
    junction(187.96, 114.3),
    junction(134.62, 114.3),
    junction(134.62, 119.38),
    junction(53.34, 119.38),
    junction(53.34, 137.16),
    junction(53.34, 152.4),
    junction(45.72, 152.4),
    junction(299.72, 114.3),
    junction(370.84, 114.3),
    text("GND", 56.0, 118.11),
]

# ESP32 3V3 rail to I2C sensors and left-side input pull-ups.
items += [
    wire(187.96, 109.22, 299.72, 109.22),
    wire(299.72, 109.22, 370.84, 109.22),
    wire(198.12, 109.22, 198.12, 96.52),
    wire(198.12, 96.52, 48.26, 96.52),
    wire(48.26, 96.52, 48.26, 134.62),
    wire(48.26, 116.84, 45.72, 116.84),
    wire(48.26, 134.62, 58.42, 134.62),
    wire(58.42, 134.62, 58.42, 149.86),
    wire(58.42, 149.86, 76.2, 149.86),
    junction(198.12, 109.22),
    junction(299.72, 109.22),
    junction(370.84, 109.22),
    junction(48.26, 116.84),
    junction(48.26, 134.62),
    junction(58.42, 134.62),
    junction(58.42, 149.86),
    junction(45.72, 116.84),
    junction(76.2, 149.86),
    text("3V3", 52.07, 95.25),
]

# I2C direct rails.
items += [
    wire(187.96, 119.38, 299.72, 119.38),
    wire(299.72, 119.38, 370.84, 119.38),
    wire(187.96, 124.46, 299.72, 124.46),
    wire(299.72, 124.46, 370.84, 124.46),
    junction(299.72, 119.38),
    junction(299.72, 124.46),
    junction(370.84, 119.38),
    junction(370.84, 124.46),
]

# Soil sensor, tank switch, and level pull-up.
items += [
    wire(81.28, 127.0, 119.38, 127.0),
    wire(119.38, 127.0, 119.38, 134.62),
    wire(119.38, 134.62, 142.24, 134.62),
    wire(45.72, 137.16, 45.72, 152.4),
    wire(45.72, 152.4, 35.56, 152.4),
    wire(45.72, 185.42, 35.56, 185.42),
    wire(76.2, 160.02, 76.2, 175.26),
    wire(76.2, 175.26, 81.28, 175.26),
    wire(81.28, 175.26, 129.54, 175.26),
    wire(129.54, 175.26, 129.54, 154.94),
    wire(129.54, 154.94, 142.24, 154.94),
    junction(119.38, 134.62),
    junction(81.28, 175.26),
    junction(35.56, 185.42),
    junction(76.2, 175.26),
    junction(129.54, 175.26),
]

# Pump driver.
items += [
    wire(264.16, 231.14, 302.26, 231.14),
    wire(302.26, 231.14, 342.9, 231.14),
    wire(142.24, 165.1, 198.12, 165.1),
    wire(198.12, 165.1, 198.12, 241.3),
    wire(198.12, 241.3, 300.99, 241.3),
    wire(318.77, 241.3, 332.74, 241.3),
    wire(322.58, 241.3, 322.58, 254.0),
    wire(322.58, 264.16, 322.58, 274.32),
    wire(342.9, 251.46, 342.9, 274.32),
    wire(388.62, 254.0, 388.62, 220.98),
    wire(388.62, 264.16, 388.62, 274.32),
    junction(302.26, 220.98),
    junction(302.26, 231.14),
    junction(322.58, 241.3),
    junction(322.58, 274.32),
    junction(342.9, 274.32),
    junction(388.62, 220.98),
    junction(388.62, 274.32),
]

body = "\n".join(items)

new_sch = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "2.0")
\t(uuid "33333333-3333-4333-8333-333333333333")
\t(paper "A2")
\t(title_block
\t\t(title "ESP32-S3 plant watering controller")
\t\t(date "2026-06-18")
\t\t(company "Generated from Sensorlist.txt")
\t)
{lib_symbols}
{body}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''

SCH.write_text(new_sch, encoding="ascii")

# Write a project-local symbol library matching all embedded PlantWatering symbols.
symbols = []
for m in re.finditer(r'\n\t\t\(symbol "PlantWatering:', lib_symbols):
    form, _ = extract_form(lib_symbols, m.start() + 3)
    symbols.append(form.replace('(symbol "PlantWatering:', '(symbol "', 1))

(OUT / "PlantWatering.kicad_sym").write_text(
    '(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "eeschema")\n\t(generator_version "2.0")\n'
    + "\n".join(symbols)
    + "\n)\n",
    encoding="ascii",
)

(OUT / "sym-lib-table").write_text(
    '(sym_lib_table\n'
    '  (version 7)\n'
    '  (lib (name "PlantWatering")(type "KiCad")(uri "${KIPRJMOD}/PlantWatering.kicad_sym")(options "")(descr "Project-local module symbols"))\n'
    ')\n',
    encoding="ascii",
)
