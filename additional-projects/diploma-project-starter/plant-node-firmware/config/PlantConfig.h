#pragma once

#include <cstdint>

namespace irrigation::plant {

struct PlantConfig {
  char device_id[32] = "plant_01";
  char plant_name[64] = "";
  char scientific_name[64] = "";
  float soil_moisture_min = 0.0F;
  float soil_moisture_target = 0.0F;
  float light_min_lux = 0.0F;
  float light_target_lux = 0.0F;
  float air_temperature_min = 0.0F;
  float air_temperature_max = 0.0F;
  float air_humidity_min = 0.0F;
  float pump_ml_per_second = 0.0F;
  float pulse_ml = 0.0F;
  float max_session_ml = 0.0F;
  float max_daily_ml = 0.0F;
  std::uint16_t lockout_minutes = 0;
  std::uint16_t settle_minutes = 0;
  float low_battery_cutoff = 0.0F;
  std::uint16_t reporting_interval_minutes = 0;
  std::uint16_t measurement_interval_minutes = 0;
  char profile_source[96] = "local";
};

}  // namespace irrigation::plant
