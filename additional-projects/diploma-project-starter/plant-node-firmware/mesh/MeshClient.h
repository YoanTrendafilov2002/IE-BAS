#pragma once

#include <cstddef>
#include <cstdint>

namespace irrigation::plant {
class MeshClient { public: bool begin(); bool join(); bool send(const std::uint8_t* data, std::size_t size); };
}  // namespace irrigation::plant
