#pragma once

#include "PlantConfig.h"

namespace irrigation::plant {

class ConfigManager {
 public:
  bool load(PlantConfig& config);
  bool save(const PlantConfig& config);
};

}  // namespace irrigation::plant
