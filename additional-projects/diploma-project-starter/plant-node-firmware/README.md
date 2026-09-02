# Plant node firmware

Тук ще живее firmware-ът на възел за една саксия. Той взема решението за поливане локално и по подразбиране държи помпата изключена.

Текущият код е само интерфейсен скелет: няма GPIO, I2C, ADC, mesh, NVS, таймери или управление на помпата. `setup()` и `loop()` са празни, така че проектът не управлява реален хардуер.

## Граници

- `config/` — локален профил на растението и бъдещо зареждане от storage.
- `sensors/` — абстракции за измерванията; без драйвери.
- `actuators/` — договор за безопасно управление на помпа; без GPIO.
- `control/` — бъдещи safety и irrigation правила.
- `mesh/` — договор към радиомрежата; без транспорт.
- `protocol/` — препратка към общия договор в `../shared/protocol`.

## Очакван жизнен цикъл (бъдеща версия)

`BOOT → LOAD_CONFIG → JOIN_MESH → SELF_TEST → MEASURE → SAFETY_CHECK → DECIDE → WATER_OR_SKIP → SETTLE → REPORT_TO_FRONT_NODE → SLEEP_OR_WAIT`
