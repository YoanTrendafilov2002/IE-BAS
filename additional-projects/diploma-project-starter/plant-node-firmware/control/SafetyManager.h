#pragma once

#include "../config/PlantConfig.h"
#include "../sensors/SensorData.h"

namespace irrigation::plant {
class SafetyManager { public: bool may_water(const PlantConfig&, const SensorData&); };
}  // namespace irrigation::plant
