#pragma once

namespace irrigation::plant {
class TankLevelSensor { public: bool begin(); bool is_low(); };
}  // namespace irrigation::plant
