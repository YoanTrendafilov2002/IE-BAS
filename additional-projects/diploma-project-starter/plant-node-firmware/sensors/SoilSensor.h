#pragma once

namespace irrigation::plant {
class SoilSensor { public: bool begin(); float read_percent(); };
}  // namespace irrigation::plant
