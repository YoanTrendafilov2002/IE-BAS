#pragma once

namespace irrigation::plant {
class EnvironmentSensor { public: bool begin(); bool read(float& temperature_c, float& humidity_percent); };
}  // namespace irrigation::plant
