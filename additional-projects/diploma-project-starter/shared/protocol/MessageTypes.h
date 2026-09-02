#pragma once

#include <cstdint>

namespace irrigation::protocol {

constexpr std::uint8_t kProtocolVersion = 1;

enum class MessageType : std::uint8_t {
  Telemetry,
  WateringEvent,
  ConfigSet,
  Command,
  CommandResult,
  Heartbeat,
  Error
};

enum class CommandKind : std::uint8_t { WaterNow, RequestConfig, Restart };
enum class ErrorCode : std::uint8_t { None, NotImplemented, InvalidPacket, SafetyRejected };

struct MessageHeader {
  std::uint8_t protocol_version = kProtocolVersion;
  MessageType type = MessageType::Telemetry;
  char device_id[32] = "";
  std::uint32_t sequence = 0;
  std::uint32_t timestamp = 0;
};

struct TelemetryPayload {
  float soil_moisture_percent = 0.0F;
  float battery_voltage = 0.0F;
  float light_lux = 0.0F;
  float air_temperature = 0.0F;
  float air_humidity = 0.0F;
  bool tank_low = true;
  bool pump_locked = true;
  ErrorCode error = ErrorCode::NotImplemented;
};

struct WateringEventPayload {
  float amount_ml = 0.0F;
  std::uint32_t duration_ms = 0;
  float soil_before = 0.0F;
  float soil_after = 0.0F;
  char reason[48] = "";
};

struct CommandPayload {
  CommandKind command = CommandKind::WaterNow;
  float amount_ml = 0.0F;
};

}  // namespace irrigation::protocol
