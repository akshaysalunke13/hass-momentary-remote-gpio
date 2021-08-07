"""Allows to configure a momentary switch using RPi remote GPIO."""
from datetime import timedelta
import voluptuous as vol
import logging, time

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import CONF_HOST, DEVICE_DEFAULT_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_point_in_time
import homeassistant.util.dt as dt_util


from . import CONF_INVERT_LOGIC, DEFAULT_INVERT_LOGIC
from .. import momentary_remote_rpi_gpio

_LOGGER = logging.getLogger(__name__)

CONF_PORTS = "ports"

_SENSORS_SCHEMA = vol.Schema({cv.positive_int: cv.string})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORTS): _SENSORS_SCHEMA,
        vol.Optional(CONF_INVERT_LOGIC, default=DEFAULT_INVERT_LOGIC): cv.boolean,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Remote Raspberry PI GPIO devices."""
    address = config[CONF_HOST]
    invert_logic = config[CONF_INVERT_LOGIC]
    ports = config[CONF_PORTS]

    devices = []
    for port, name in ports.items():
        try:
            led = momentary_remote_rpi_gpio.setup_output(address, port, invert_logic)
        except (ValueError, IndexError, KeyError, OSError):
            return
        new_switch = MomentaryRemoteRPiGPIOSwitch(name, led)
        devices.append(new_switch)

    add_entities(devices)


class MomentaryRemoteRPiGPIOSwitch(SwitchEntity):
    """Representation of a Remote Raspberry Pi GPIO."""

    def __init__(self, name, led):
        """Initialize the pin."""
        self._name = name or DEVICE_DEFAULT_NAME
        self._state = False
        self._switch = led
        self._toggle_for = timedelta(seconds=0.5)
        self._toggle_until = None

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def assumed_state(self):
        """If unable to access real state of the entity."""
        return True

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def state(self):
        """Return the state of the switch."""
        if self._toggle_until is not None:
            if self._toggle_until > time.monotonic():
                return self._state
            # Turned Off
            self._toggle_until = None
            momentary_remote_rpi_gpio.write_output(self._switch, 0)
            self._state = False
            _LOGGER.debug("turned off")
        return self._state

    def turn_on(self, **kwargs):
        self._activate()

    def turn_off(self, **kwargs):
        self._activate()

    def _activate(self):
        """Turn the switch on."""
        self._toggle_until = time.monotonic() + self._toggle_for.total_seconds()
        track_point_in_time(
            self.hass,
            self.async_update_ha_state,
            dt_util.utcnow() + self._toggle_for,
        )
        momentary_remote_rpi_gpio.write_output(self._switch, 1)
        self._state = True
        _LOGGER.debug("turned on")
        self.schedule_update_ha_state()
