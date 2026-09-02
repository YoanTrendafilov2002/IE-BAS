# Комуникационен протокол — версия 0.1 (договор)

## Обхват и ограничения

Протоколът описва логическите съобщения между plant node, front node и backend. Реален радиотранспорт и сериализация не са имплементирани в този етап. MQTT не се използва. Front node предава данни към backend чрез HTTP/REST в бъдеща версия.

Всяко съобщение носи `protocol_version`, `type`, `device_id`, `seq` и `timestamp`. `seq` позволява откриване на повторения, но стратегията за съхранение и потвърждение остава за следващ етап.

## Типове съобщения

| Тип | Посока | Предназначение |
| --- | --- | --- |
| `telemetry` | plant → front → backend | Периодични измервания и текущ статус. |
| `watering_event` | plant → front → backend | Факт за извършено или отказано поливане. |
| `config_set` | backend → front → plant | Предложена промяна на локалния профил. |
| `command` | backend → front → plant | Искане, например `water_now`; не е безусловна команда. |
| `command_result` | plant → front → backend | Прието, отказано или неимплементирано искане. |
| `heartbeat` | plant ↔ front | Бъдеща проверка за наличност. |
| `error` | plant/front → backend | Диагностично събитие. |

## Пример: telemetry

```json
{
  "protocol_version": 1,
  "type": "telemetry",
  "device_id": "plant_01",
  "seq": 100,
  "timestamp": 0,
  "soil_moisture_percent": 34.5,
  "battery_voltage": 3.82,
  "battery_state": "OK",
  "light_lux": 420.0,
  "air_temperature": 24.1,
  "air_humidity": 48.2,
  "tank_low": false,
  "pump_locked": false,
  "error": "NONE"
}
```

## Пример: watering_event

```json
{
  "protocol_version": 1,
  "type": "watering_event",
  "device_id": "plant_01",
  "seq": 101,
  "amount_ml": 10.0,
  "duration_ms": 3200,
  "soil_before": 28.4,
  "soil_after": 31.9,
  "reason": "LOW_SOIL_MOISTURE"
}
```

## Пример: config_set

```json
{
  "protocol_version": 1,
  "type": "config_set",
  "device_id": "plant_01",
  "soil_moisture_min": 30.0,
  "soil_moisture_target": 45.0,
  "pulse_ml": 10.0,
  "max_daily_ml": 120.0,
  "lockout_minutes": 180
}
```

## Пример: command и локална защита

```json
{
  "protocol_version": 1,
  "type": "command",
  "device_id": "plant_01",
  "command": "water_now",
  "amount_ml": 10.0
}
```

Plant node валидира заряда на батерията, нивото на резервоара, достоверността на сензора, максималното количество за сесия/ден и времето за блокировка. При неуспех изпраща `command_result` с причина за отказ. Серверът и front node никога не заобикалят тези проверки.

## Бъдещи решения

- Избор и измерване на максималната дължина на радиопакет.
- Формат на бинарната сериализация или JSON-over-transport.
- Потвърждения, retries, timeout-и и дублиране.
- Автентикация и защита срещу replay за командите.
