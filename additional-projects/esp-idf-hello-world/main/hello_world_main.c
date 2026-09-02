#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "hello_world";

void app_main(void)
{
    esp_chip_info_t chip_info;
    uint32_t flash_size;

    esp_chip_info(&chip_info);
    ESP_LOGI(TAG, "Hello from ESP-IDF!");
    ESP_LOGI(TAG, "CPU cores: %d", chip_info.cores);

    if (esp_flash_get_size(NULL, &flash_size) == ESP_OK) {
        ESP_LOGI(TAG, "Flash size: %lu MB", flash_size / (1024 * 1024));
    }

    for (int seconds = 5; seconds > 0; seconds--) {
        ESP_LOGI(TAG, "Restarting in %d seconds", seconds);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    esp_restart();
}
