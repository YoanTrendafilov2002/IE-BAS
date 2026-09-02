#!/usr/bin/env python3
"""Direct electronic configuration for the modular irrigation plant node.

This is the configuration layer before KiCad/app work. It models the wiring as
named nets so every connection is explicit and auditable.

Sources used for this pass:
- Project brief: C:/Users/user/Downloads/codex_project_brief_modular_irrigation.md
- YouTube metadata: "Kicad schematics and PCB Python scripting"
- K010 product page check: Elimex lists K010 as a 10-16 V relay controller.
- Replacement level switch: Elimex XSL-4510-P passive float switch.

Design decision for this draft:
- The K585 boost converter is set to 5 V and powers ESP32 VIN/5V plus pump.
- Battery voltage is measured on the switched LiPo/system side before boost.
- The tank level input uses a passive float switch with a 10k pull-up to 3.3 V.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Iterable


PINOUT = {
    # Chosen ESP32-S3 GPIOs. Verify the exact board silkscreen before soldering.
    "soil_adc": "GPIO1_ADC1_CH0",
    "battery_adc": "GPIO2_ADC1_CH1",
    "pump_gate": "GPIO5",
    "level_input": "GPIO6",
    "i2c_sda": "GPIO8",
    "i2c_scl": "GPIO9",
}


@dataclass(frozen=True)
class Component:
    ref: str
    value: str
    role: str


@dataclass(frozen=True)
class Connection:
    net: str
    endpoint: str
    note: str = ""


@dataclass(frozen=True)
class Issue:
    severity: str
    item: str
    message: str


COMPONENTS = [
    Component("BAT1", "Li-Po 103450 3.7V 2000mAh", "Battery source"),
    Component("U_CHG", "K548 USB-C Li-ion/LiPo charger", "Battery charger and load output"),
    Component("SW1", "Small slide/rocker switch", "Main system power switch"),
    Component("U_BOOST", "K585 boost converter set to 5.00 V", "5 V rail for ESP32 VIN and pump"),
    Component("U_ESP", "ESP32-S3-Zero mini development board", "Plant-node MCU"),
    Component("U_LIGHT", "GY-302 BH1750", "I2C light sensor"),
    Component("U_AIR", "SHT30/SHT31 housed sensor", "I2C air temperature/humidity sensor"),
    Component("U_SOIL", "K2112 soil moisture sensor", "Analog soil moisture sensor"),
    Component("SW_LEVEL", "XSL-4510-P float level switch", "Passive NC tank level switch"),
    Component("PUMP1", "DC water pump 3-5V / 200mA", "Irrigation pump"),
    Component("Q1", "IRLB3034 or IRLZ44N", "Low-side pump MOSFET"),
    Component("D1", "1N5819", "Pump flyback diode"),
    Component("C1", "470uF/16V electrolytic", "Pump rail bulk capacitor"),
    Component("R_GATE", "100 ohm", "Series resistor from ESP32 GPIO to MOSFET gate"),
    Component("R_PD", "10k ohm", "MOSFET gate pulldown"),
    Component("R_LEVEL", "10k ohm", "Tank level pull-up"),
    Component("R_BAT_H", "100k ohm", "Battery divider high side"),
    Component("R_BAT_L", "100k ohm", "Battery divider low side"),
]


# Direct wiring model. A net is one electrical node; every listed endpoint on a
# net is directly connected to every other endpoint on that same net.
CONNECTIONS = [
    # Battery and charger input
    Connection("BAT_PLUS_RAW", "BAT1.+", "Battery red wire"),
    Connection("BAT_PLUS_RAW", "U_CHG.B+", "Charger battery positive"),
    Connection("GND", "BAT1.-", "Battery black wire"),
    Connection("GND", "U_CHG.B-", "Charger battery negative"),
    Connection("GND", "U_CHG.OUT-", "Charger load/output negative"),
    # Switched battery/system side before boost
    Connection("CHARGER_OUT_PLUS", "U_CHG.OUT+", "Charger load/output positive"),
    Connection("CHARGER_OUT_PLUS", "SW1.1", "Main switch input"),
    Connection("SWITCHED_BAT_PLUS", "SW1.2", "Main switch output"),
    Connection("SWITCHED_BAT_PLUS", "U_BOOST.IN+", "Boost converter input positive"),
    Connection("GND", "U_BOOST.IN-", "Boost converter input negative"),
    # Battery voltage divider senses the switched LiPo/system voltage, not boost 5 V.
    Connection("SWITCHED_BAT_PLUS", "R_BAT_H.1", "Battery ADC divider top"),
    Connection("BATTERY_ADC", "R_BAT_H.2", "Battery ADC divider midpoint"),
    Connection("BATTERY_ADC", "R_BAT_L.1", "Battery ADC divider midpoint"),
    Connection("BATTERY_ADC", f"U_ESP.{PINOUT['battery_adc']}", "ESP32 battery ADC input"),
    Connection("GND", "R_BAT_L.2", "Battery ADC divider bottom"),
    # 5 V boosted rail
    Connection("+5V_BOOST", "U_BOOST.OUT+", "Boost output positive, trim to 5.00 V before use"),
    Connection("GND", "U_BOOST.OUT-", "Boost output negative/common ground"),
    Connection("+5V_BOOST", "U_ESP.5V/VIN", "ESP32 board 5 V/VIN input"),
    Connection("GND", "U_ESP.GND", "ESP32 ground"),
    # 3.3 V logic/sensor rail from ESP32 board regulator
    Connection("+3V3_LOGIC", "U_ESP.3V3", "ESP32 regulated 3.3 V output"),
    Connection("+3V3_LOGIC", "U_LIGHT.VCC", "BH1750 supply"),
    Connection("+3V3_LOGIC", "U_AIR.VCC", "SHT30/SHT31 supply"),
    Connection("+3V3_LOGIC", "U_SOIL.VCC", "Soil sensor supply"),
    Connection("GND", "U_LIGHT.GND", "BH1750 ground"),
    Connection("GND", "U_AIR.GND", "SHT30/SHT31 ground"),
    Connection("GND", "U_SOIL.GND", "Soil sensor ground"),
    # I2C bus
    Connection("I2C_SDA", f"U_ESP.{PINOUT['i2c_sda']}", "ESP32 I2C SDA"),
    Connection("I2C_SDA", "U_LIGHT.SDA", "BH1750 SDA"),
    Connection("I2C_SDA", "U_AIR.SDA", "SHT30/SHT31 SDA"),
    Connection("I2C_SCL", f"U_ESP.{PINOUT['i2c_scl']}", "ESP32 I2C SCL"),
    Connection("I2C_SCL", "U_LIGHT.SCL", "BH1750 SCL"),
    Connection("I2C_SCL", "U_AIR.SCL", "SHT30/SHT31 SCL"),
    # Analog soil sensor
    Connection("SOIL_ADC", "U_SOIL.AO", "Soil sensor analog output"),
    Connection("SOIL_ADC", f"U_ESP.{PINOUT['soil_adc']}", "ESP32 soil ADC input"),
    # Passive tank-level switch. XSL-4510-P is NC, so firmware can invert logic
    # or the float can be mechanically flipped if the installation allows it.
    Connection("+3V3_LOGIC", "R_LEVEL.1", "Tank level pull-up high side"),
    Connection("TANK_LEVEL", "R_LEVEL.2", "Tank level pull-up low side"),
    Connection("TANK_LEVEL", "SW_LEVEL.1", "XSL-4510-P contact lead 1"),
    Connection("TANK_LEVEL", f"U_ESP.{PINOUT['level_input']}", "ESP32 tank level input"),
    Connection("GND", "SW_LEVEL.2", "XSL-4510-P contact lead 2"),
    # Pump supply and MOSFET low-side switch
    Connection("+5V_BOOST", "PUMP1.+", "Pump positive"),
    Connection("PUMP_LOW", "PUMP1.-", "Pump negative"),
    Connection("PUMP_LOW", "Q1.D", "MOSFET drain"),
    Connection("GND", "Q1.S", "MOSFET source"),
    Connection("PUMP_GPIO", f"U_ESP.{PINOUT['pump_gate']}", "Pump control GPIO"),
    Connection("PUMP_GPIO", "R_GATE.1", "Gate resistor input"),
    Connection("MOSFET_GATE", "R_GATE.2", "Gate resistor output"),
    Connection("MOSFET_GATE", "Q1.G", "MOSFET gate"),
    Connection("MOSFET_GATE", "R_PD.1", "Gate pulldown high side"),
    Connection("GND", "R_PD.2", "Gate pulldown low side"),
    # Pump protection
    Connection("+5V_BOOST", "D1.K", "Flyback diode cathode/stripe side"),
    Connection("PUMP_LOW", "D1.A", "Flyback diode anode/non-stripe side"),
    Connection("+5V_BOOST", "C1.+", "Bulk capacitor positive"),
    Connection("GND", "C1.-", "Bulk capacitor negative"),
]


ISSUES = [
    Issue(
        "DECISION",
        "XSL-4510-P float switch",
        "Recommended replacement for K010. It is a passive NC magnetic float "
        "switch, so it can be read safely as a 3.3 V GPIO contact with a 10k "
        "pull-up. Confirm final wet/dry polarity after mounting and invert in "
        "firmware if needed.",
    ),
    Issue(
        "REJECTED",
        "K010 liquid-level controller",
        "Do not use K010 directly in this battery plant node; Elimex lists it "
        "as a 10-16 V relay controller. It would require a separate higher "
        "voltage supply path.",
    ),
]


def grouped_by_net(connections: Iterable[Connection]) -> dict[str, list[Connection]]:
    nets: dict[str, list[Connection]] = defaultdict(list)
    for connection in connections:
        nets[connection.net].append(connection)
    return dict(sorted(nets.items()))


def endpoint_component(endpoint: str) -> str:
    return endpoint.split(".", 1)[0]


def validate() -> list[Issue]:
    issues: list[Issue] = []
    nets = grouped_by_net(CONNECTIONS)

    required_nets = {
        "GND",
        "+5V_BOOST",
        "+3V3_LOGIC",
        "I2C_SDA",
        "I2C_SCL",
        "SOIL_ADC",
        "TANK_LEVEL",
        "BATTERY_ADC",
        "PUMP_GPIO",
        "MOSFET_GATE",
        "PUMP_LOW",
    }
    missing = sorted(required_nets - set(nets))
    for net in missing:
        issues.append(Issue("ERROR", net, "Required net is missing."))

    for net_name in ("I2C_SDA", "I2C_SCL"):
        endpoints = {connection.endpoint for connection in nets.get(net_name, [])}
        if not any(endpoint.startswith("U_ESP.") for endpoint in endpoints):
            issues.append(Issue("ERROR", net_name, "I2C net has no ESP32 endpoint."))
        if len(endpoints) < 3:
            issues.append(Issue("ERROR", net_name, "I2C net should reach ESP32 and both I2C sensors."))

    five_v_endpoints = {connection.endpoint for connection in nets.get("+5V_BOOST", [])}
    forbidden_gpio_on_5v = [
        endpoint
        for endpoint in five_v_endpoints
        if endpoint.startswith("U_ESP.GPIO") or "ADC" in endpoint
    ]
    if forbidden_gpio_on_5v:
        issues.append(
            Issue(
                "ERROR",
                "+5V_BOOST",
                "5 V boost rail touches GPIO/ADC endpoints: " + ", ".join(forbidden_gpio_on_5v),
            )
        )

    gnd_components = {endpoint_component(connection.endpoint) for connection in nets.get("GND", [])}
    for ref in ("U_CHG", "U_BOOST", "U_ESP", "U_LIGHT", "U_AIR", "U_SOIL", "Q1"):
        if ref not in gnd_components:
            issues.append(Issue("ERROR", "GND", f"{ref} is not tied to common ground."))

    pump_low = {connection.endpoint for connection in nets.get("PUMP_LOW", [])}
    if not {"PUMP1.-", "Q1.D", "D1.A"}.issubset(pump_low):
        issues.append(Issue("ERROR", "PUMP_LOW", "Pump negative, MOSFET drain, and diode anode must share net."))

    mosfet_gate = {connection.endpoint for connection in nets.get("MOSFET_GATE", [])}
    if not {"R_GATE.2", "Q1.G", "R_PD.1"}.issubset(mosfet_gate):
        issues.append(Issue("ERROR", "MOSFET_GATE", "Gate resistor, MOSFET gate, and pulldown must share net."))

    tank_level = {connection.endpoint for connection in nets.get("TANK_LEVEL", [])}
    expected_tank_level = {"R_LEVEL.2", "SW_LEVEL.1", f"U_ESP.{PINOUT['level_input']}"}
    if not expected_tank_level.issubset(tank_level):
        issues.append(Issue("ERROR", "TANK_LEVEL", "Tank pull-up, float switch, and ESP32 input must share net."))

    issues.extend(ISSUES)
    return issues


def as_model() -> dict:
    return {
        "pinout": PINOUT,
        "components": [asdict(component) for component in COMPONENTS],
        "nets": {
            net: [asdict(connection) for connection in connections]
            for net, connections in grouped_by_net(CONNECTIONS).items()
        },
        "issues": [asdict(issue) for issue in validate()],
    }


def emit_markdown() -> str:
    model = as_model()
    lines: list[str] = []
    lines.append("# Modular Irrigation Plant Node - Electronic Configuration")
    lines.append("")
    lines.append("## Pin Assignments")
    lines.append("")
    lines.append("| Function | ESP32-S3 pin |")
    lines.append("|---|---|")
    for function, pin in model["pinout"].items():
        lines.append(f"| {function} | {pin} |")

    lines.append("")
    lines.append("## Direct Nets")
    lines.append("")
    for net, connections in model["nets"].items():
        lines.append(f"### {net}")
        lines.append("")
        lines.append("| Endpoint | Note |")
        lines.append("|---|---|")
        for connection in connections:
            lines.append(f"| {connection['endpoint']} | {connection['note']} |")
        lines.append("")

    lines.append("## Issues / Decisions")
    lines.append("")
    lines.append("| Severity | Item | Message |")
    lines.append("|---|---|---|")
    for issue in model["issues"]:
        lines.append(f"| {issue['severity']} | {issue['item']} | {issue['message']} |")
    lines.append("")
    return "\n".join(lines)


def emit_json() -> str:
    return json.dumps(as_model(), indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero if there are ERROR or BLOCKER issues.",
    )
    args = parser.parse_args()

    print(emit_json() if args.format == "json" else emit_markdown())

    if args.strict:
        severities = {issue.severity for issue in validate()}
        if {"ERROR", "BLOCKER"} & severities:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
