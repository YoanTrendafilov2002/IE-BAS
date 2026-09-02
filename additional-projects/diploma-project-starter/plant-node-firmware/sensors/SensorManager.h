#pragma once

#include "SensorData.h"

namespace irrigation::plant {

class SensorManager {
 public:
  bool begin();
  SensorData read_all();
};

}  // namespace irrigation::plant
