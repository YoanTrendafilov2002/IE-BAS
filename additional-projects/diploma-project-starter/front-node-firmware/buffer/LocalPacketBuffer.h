#pragma once

#include <cstddef>
#include <cstdint>

namespace irrigation::front { class LocalPacketBuffer { public: bool enqueue(const std::uint8_t* data, std::size_t size); bool flush(); }; }
