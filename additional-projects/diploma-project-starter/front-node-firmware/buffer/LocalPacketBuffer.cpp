#include "LocalPacketBuffer.h"
namespace irrigation::front { bool LocalPacketBuffer::enqueue(const std::uint8_t*, std::size_t) { return false; } bool LocalPacketBuffer::flush() { return false; } }
