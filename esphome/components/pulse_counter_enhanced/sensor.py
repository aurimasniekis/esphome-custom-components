from esphome import automation, pins
import esphome.codegen as cg
from esphome.components import sensor
import esphome.config_validation as cv
from esphome.const import (
    CONF_COUNT_MODE,
    CONF_FALLING_EDGE,
    CONF_ID,
    CONF_INTERNAL_FILTER,
    CONF_NUMBER,
    CONF_PIN,
    CONF_RISING_EDGE,
    CONF_TOTAL,
    CONF_VALUE,
    ICON_PULSE,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    UNIT_PULSES,
    UNIT_PULSES_PER_MINUTE,
)
from esphome.core import CORE

CONF_USE_PCNT = "use_pcnt"

pulse_counter_enhanced_ns = cg.esphome_ns.namespace("pulse_counter_enhanced")
PulseCounterEnhancedCountMode = pulse_counter_enhanced_ns.enum("PulseCounterEnhancedCountMode")
COUNT_MODES = {
    "DISABLE": PulseCounterEnhancedCountMode.PULSE_COUNTER_DISABLE,
    "INCREMENT": PulseCounterEnhancedCountMode.PULSE_COUNTER_INCREMENT,
    "DECREMENT": PulseCounterEnhancedCountMode.PULSE_COUNTER_DECREMENT,
}

COUNT_MODE_SCHEMA = cv.enum(COUNT_MODES, upper=True)

PulseCounterEnhancedSensor = pulse_counter_enhanced_ns.class_(
    "PulseCounterEnhancedSensor", sensor.Sensor, cg.PollingComponent
)

SetTotalPulsesAction = pulse_counter_enhanced_ns.class_(
    "SetTotalPulsesAction", automation.Action
)


def validate_internal_filter(value):
    use_pcnt = value.get(CONF_USE_PCNT)
    if CORE.is_esp8266 and use_pcnt:
        raise cv.Invalid(
            "Using hardware PCNT is only available on ESP32",
            [CONF_USE_PCNT],
        )

    if CORE.is_esp32 and use_pcnt:
        if value.get(CONF_INTERNAL_FILTER).total_microseconds > 13:
            raise cv.Invalid(
                "Maximum internal filter value when using ESP32 hardware PCNT is 13us",
                [CONF_INTERNAL_FILTER],
            )

    return value


def validate_pulse_counter_pin(value):
    value = pins.internal_gpio_input_pin_schema(value)
    if CORE.is_esp8266 and value[CONF_NUMBER] >= 16:
        raise cv.Invalid(
            "Pins GPIO16 and GPIO17 cannot be used as pulse counters on ESP8266."
        )
    return value


def validate_count_mode(value):
    rising_edge = value[CONF_RISING_EDGE]
    falling_edge = value[CONF_FALLING_EDGE]
    if rising_edge == "DISABLE" and falling_edge == "DISABLE":
        raise cv.Invalid(
            "Can't set both count modes to DISABLE! This means no counting occurs at "
            "all!"
        )
    return value


CONFIG_SCHEMA = cv.All(
    sensor.sensor_schema(
        PulseCounterEnhancedSensor,
        unit_of_measurement=UNIT_PULSES_PER_MINUTE,
        icon=ICON_PULSE,
        accuracy_decimals=2,
        state_class=STATE_CLASS_MEASUREMENT,
    )
    .extend(
        {
            cv.Required(CONF_PIN): validate_pulse_counter_pin,
            cv.Optional(
                CONF_COUNT_MODE,
                default={
                    CONF_RISING_EDGE: "INCREMENT",
                    CONF_FALLING_EDGE: "DISABLE",
                },
            ): cv.All(
                cv.Schema(
                    {
                        cv.Required(CONF_RISING_EDGE): COUNT_MODE_SCHEMA,
                        cv.Required(CONF_FALLING_EDGE): COUNT_MODE_SCHEMA,
                    }
                ),
                validate_count_mode,
            ),
            cv.SplitDefault(CONF_USE_PCNT, esp32=True): cv.boolean,
            cv.Optional(
                CONF_INTERNAL_FILTER, default="13us"
            ): cv.positive_time_period_microseconds,
            cv.Optional(CONF_TOTAL): sensor.sensor_schema(
                unit_of_measurement=UNIT_PULSES,
                icon=ICON_PULSE,
                accuracy_decimals=0,
                state_class=STATE_CLASS_TOTAL_INCREASING,
            ),
        },
    )
    .extend(cv.polling_component_schema("60s")),
    validate_internal_filter,
)


async def to_code(config):
    var = await sensor.new_sensor(config, config.get(CONF_USE_PCNT))
    await cg.register_component(var, config)

    pin = await cg.gpio_pin_expression(config[CONF_PIN])
    cg.add(var.set_pin(pin))
    count = config[CONF_COUNT_MODE]
    cg.add(var.set_rising_edge_mode(count[CONF_RISING_EDGE]))
    cg.add(var.set_falling_edge_mode(count[CONF_FALLING_EDGE]))
    cg.add(var.set_filter_us(config[CONF_INTERNAL_FILTER]))

    if CONF_TOTAL in config:
        sens = await sensor.new_sensor(config[CONF_TOTAL])
        cg.add(var.set_total_sensor(sens))


@automation.register_action(
    "pulse_counter_enhanced.set_total_pulses",
    SetTotalPulsesAction,
    cv.Schema(
        {
            cv.Required(CONF_ID): cv.use_id(PulseCounterEnhancedSensor),
            cv.Required(CONF_VALUE): cv.templatable(cv.uint32_t),
        }
    ),
)
async def set_total_action_to_code(config, action_id, template_arg, args):
    paren = await cg.get_variable(config[CONF_ID])
    var = cg.new_Pvariable(action_id, template_arg, paren)
    template_ = await cg.templatable(config[CONF_VALUE], args, int)
    cg.add(var.set_total_pulses(template_))
    return var