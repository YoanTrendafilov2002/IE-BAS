#pragma once

#include <cstdint>

namespace irrigation::plant {

enum class PumpResult : std::uint8_t { NotImplemented, Started, RejectedBySafety, Fault };

class PumpController {
 public:
  bool begin();
  void force_off();
  PumpResult run_for(std::uint32_t duration_ms);
};

}  // namespace irrigation::plant
