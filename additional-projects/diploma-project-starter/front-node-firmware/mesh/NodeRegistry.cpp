#include "NodeRegistry.h"
namespace irrigation::front { bool NodeRegistry::upsert(const NodeRecord&) { return false; } bool NodeRegistry::mark_offline(std::uint32_t) { return false; } }
