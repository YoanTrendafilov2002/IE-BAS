#pragma once

#include "../config/PlantConfig.h"
#include "../sensors/SensorData.h"

namespace irrigation::plant {

enum class IrrigationDecision { Undecided, Skip, Water, RejectUnsafeCommand };
class IrrigationController { public: IrrigationDecision evaluate(const PlantConfig&, const SensorData&); };

}  // namespace irrigation::plant
