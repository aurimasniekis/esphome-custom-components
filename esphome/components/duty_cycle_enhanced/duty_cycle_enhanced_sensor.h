#pragma once

#include "esphome/core/component.h"
#include "esphome/core/hal.h"
#include "esphome/components/sensor/sensor.h"

namespace esphome {
namespace duty_cycle_enhanced {

/// Store data in a class that doesn't use multiple-inheritance (vtables in flash)
struct DutyCycleEnhancedSensorStore {
  volatile uint32_t last_interrupt{0};
  volatile uint32_t on_time{0};
  volatile bool last_level{false};
  ISRInternalGPIOPin pin;

  static void gpio_intr(DutyCycleEnhancedSensorStore *arg);
};

class DutyCycleEnhancedSensor : public sensor::Sensor, public PollingComponent {
 public:
  void set_pin(InternalGPIOPin *pin) { pin_ = pin; }

  void setup() override;
  float get_setup_priority() const override;
  void dump_config() override;
  void update() override;

  void reset() {
    this->store_.last_interrupt = micros();
    this->store_.on_time = 0;
    this->store_.last_level = this->pin_->digital_read();

    this->last_update_ = 0;
  }

 protected:
  InternalGPIOPin *pin_;

  DutyCycleEnhancedSensorStore store_{};
  uint32_t last_update_{0};
};

}  // namespace duty_cycle_enhanced
}  // namespace esphome