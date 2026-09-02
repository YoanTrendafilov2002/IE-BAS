#pragma once

namespace irrigation::plant {
class BatteryMonitor { public: bool begin(); float read_voltage(); };
}  // namespace irrigation::plant
