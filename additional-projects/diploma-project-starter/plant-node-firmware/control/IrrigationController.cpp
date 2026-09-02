#include "IrrigationController.h"
namespace irrigation::plant { IrrigationDecision IrrigationController::evaluate(const PlantConfig&, const SensorData&) { return IrrigationDecision::Undecided; } }
