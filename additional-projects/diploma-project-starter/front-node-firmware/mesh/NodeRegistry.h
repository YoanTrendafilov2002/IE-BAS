#pragma once

#include <cstdint>

namespace irrigation::front { struct NodeRecord { char device_id[32] = ""; std::uint32_t last_seen = 0; bool online = false; }; class NodeRegistry { public: bool upsert(const NodeRecord& node); bool mark_offline(std::uint32_t timeout_seconds); }; }
