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

CONF_PORTS = "ports"

_SENSORS_SCHEMA = vol.Schema({cv.positive_int: cv.string})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORTS): _SENSORS_SCHEMA,
        vol.Optional(CONF_INVERT_LOGIC, default=DEFAULT_INVERT_LOGIC): cv.boolean,
    }
)

## Constants for MomentarySwitch
_LOGGER = logging.getLogger(__name__)

MODE = "old"
CANCELLABLE = False
TOGGLE_FOR_DEFAULT = timedelta(seconds=1)

CONF_NAME = "name"
CONF_MODE = "mode"
CONF_ON_FOR = "on_for"
CONF_ALLOW_OFF = "allow_off"
CONF_TOGGLE_FOR = "toggle_for"
CONF_CANCELLABLE = "cancellable"

# Set schema for MomentarySwitch
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_MODE, default=MODE): cv.string,
        vol.Optional(CONF_ON_FOR, default=TOGGLE_FOR_DEFAULT): vol.All(
            cv.time_period, cv.positive_timedelta
        ),
        vol.Optional(CONF_ALLOW_OFF, default=CANCELLABLE): cv.boolean,
        vol.Optional(CONF_TOGGLE_FOR, default=TOGGLE_FOR_DEFAULT): vol.All(
            cv.time_period, cv.positive_timedelta
        ),
        vol.Optional(CONF_CANCELLABLE, default=CANCELLABLE): cv.boolean,
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
            led = hass_momentary_remote_gpio.setup_output(address, port, invert_logic)
        except (ValueError, IndexError, KeyError, OSError):
            return
        new_switch = MomentaryRemoteRPiGPIOSwitch(name, led)
        devices.append(new_switch)

    add_entities(devices)


class MomentarySwitch(SwitchEntity):
    """Representation of a Momentary switch."""

    def __init__(self, config):
        """Initialize the Momentary switch device."""
        self._name = config.get(CONF_NAME)

        # Are we adding the domain or not?
        self.no_domain_ = self._name.startswith("!")
        if self.no_domain_:
            self._name = self.name[1:]
        self._unique_id = self._name.lower().replace(" ", "_")

        self._mode = config.get(CONF_MODE)
        self._toggle_until = None

        # Old configuration - only turns on
        if self._mode == "old":
            self._toggle_for = config.get(CONF_ON_FOR)
            self._cancellable = config.get(CONF_ALLOW_OFF)
            self._toggled = "on"
            self._not_toggled = "off"
            _LOGGER.debug("old config, turning on")

        # New configuration - can be either turn off or on.
        else:
            self._toggle_for = config.get(CONF_TOGGLE_FOR)
            self._cancellable = config.get(CONF_CANCELLABLE)
            if self._mode == "True":
                self._toggled = "on"
                self._not_toggled = "off"
            else:
                self._toggled = "off"
                self._not_toggled = "on"
            _LOGGER.debug("new config, turning {}".format(self._toggled))

        _LOGGER.info("MomentarySwitch: {} created".format(self._name))

    @property
    def name(self):
        if self.no_domain_:
            return self._name
        else:
            return super().name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the switch."""
        if self._toggle_until is not None:
            if self._toggle_until > time.monotonic():
                return self._toggled
            _LOGGER.debug("turned off")
            self._toggle_until = None
        return self._not_toggled

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.state == "on"

    @property
    def is_off(self):
        """Return true if switch is on."""
        return not self.is_on

    def turn_on(self, **kwargs):
        self._activate("on")

    def turn_off(self, **kwargs):
        self._activate("off")

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attrs = {
            "friendly_name": self._name,
            "unique_id": self._unique_id,
        }
        return attrs

    def _activate(self, on_off):
        """Turn the switch on."""
        if self._toggled == on_off:
            self._toggle_until = time.monotonic() + self._toggle_for.total_seconds()
            track_point_in_time(
                self.hass,
                self.async_update_ha_state,
                dt_util.utcnow() + self._toggle_for,
            )
            _LOGGER.debug("turned on")
        elif self._cancellable:
            self._toggle_until = None
            _LOGGER.debug("forced off")
        self.async_schedule_update_ha_state()


class MomentaryRemoteRPiGPIOSwitch(MomentarySwitch):
    """Representation of a Remote Raspberry Pi GPIO."""

    def __init__(self, name, led):
        """Initialize the pin."""
        self._name = name or DEVICE_DEFAULT_NAME
        self._state = False
        self._switch = led

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

    def turn_on(self, **kwargs):
        """Turn the device on."""
        hass_momentary_remote_gpio.write_output(self._switch, 1)
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        hass_momentary_remote_gpio.write_output(self._switch, 0)
        self._state = False
        self.schedule_update_ha_state()
