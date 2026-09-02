#include "PumpController.h"
namespace irrigation::plant { bool PumpController::begin() { return false; } void PumpController::force_off() {} PumpResult PumpController::run_for(std::uint32_t) { return PumpResult::NotImplemented; } }
