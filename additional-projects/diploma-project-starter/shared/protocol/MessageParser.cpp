#include "MessageParser.h"

namespace irrigation::protocol {

bool MessageParser::parse_header(const std::uint8_t*, std::size_t, MessageHeader&) const { return false; }
bool MessageParser::serialize_telemetry(const MessageHeader&, const TelemetryPayload&, std::uint8_t*, std::size_t, std::size_t& written) const {
  written = 0;
  return false;
}

}  // namespace irrigation::protocol
