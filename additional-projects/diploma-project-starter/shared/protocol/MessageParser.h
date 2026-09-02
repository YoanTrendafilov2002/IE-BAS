#pragma once

#include <cstddef>
#include <cstdint>

#include "MessageTypes.h"

namespace irrigation::protocol {

class MessageParser {
 public:
  bool parse_header(const std::uint8_t* data, std::size_t size, MessageHeader& header) const;
  bool serialize_telemetry(const MessageHeader& header, const TelemetryPayload& payload,
                           std::uint8_t* out, std::size_t capacity, std::size_t& written) const;
};

}  // namespace irrigation::protocol
