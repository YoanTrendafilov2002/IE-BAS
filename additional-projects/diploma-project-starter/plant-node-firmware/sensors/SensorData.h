#pragma once

#include <cstdint>

namespace irrigation::plant {

enum class BatteryState : std::uint8_t { Unknown, Ok, Low, Critical };
enum class SensorError : std::uint8_t { None, NotImplemented, InvalidReading, TransportFailure };

struct SensorData {
  float soil_moisture_percent = 0.0F;
  float battery_voltage = 0.0F;
  BatteryState battery_state = BatteryState::Unknown;
  float light_lux = 0.0F;
  float air_temperature = 0.0F;
  float air_humidity = 0.0F;
  bool tank_low = true;
  bool soil_sensor_valid = false;
  std::uint32_t timestamp = 0;
  SensorError error_code = SensorError::NotImplemented;
};

}  // namespace irrigation::plant
