#pragma once

#include <cstddef>
#include <cstdint>

namespace irrigation::plant {
class StorageManager { public: bool begin(); bool read(const char* key, std::uint8_t* data, std::size_t size); bool write(const char* key, const std::uint8_t* data, std::size_t size); };
}  // namespace irrigation::plant
