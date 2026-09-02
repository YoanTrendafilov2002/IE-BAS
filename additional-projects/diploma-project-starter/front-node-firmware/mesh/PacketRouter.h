#pragma once

#include <cstddef>
#include <cstdint>

namespace irrigation::front { class PacketRouter { public: bool route_to_node(const char* device_id, const std::uint8_t* packet, std::size_t size); }; }
