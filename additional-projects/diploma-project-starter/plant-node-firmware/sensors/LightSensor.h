#pragma once

namespace irrigation::plant {
class LightSensor { public: bool begin(); float read_lux(); };
}  // namespace irrigation::plant
