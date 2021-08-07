"""Support for controlling GPIO pins of a Raspberry Pi."""
import logging
from gpiozero import LED
from gpiozero.pins.pigpio import PiGPIOFactory

CONF_BOUNCETIME = "bouncetime"
CONF_INVERT_LOGIC = "invert_logic"
CONF_PULL_MODE = "pull_mode"

DEFAULT_BOUNCETIME = 50
DEFAULT_INVERT_LOGIC = True
DEFAULT_PULL_MODE = "UP"

DOMAIN = "momentary_remote_rpi_gpio"

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    """Set up the Raspberry Pi Remote GPIO component."""
    return True


def setup_output(address, port, invert_logic):
    """Set up a GPIO as output."""

    try:
        return LED(
            port, active_high=not invert_logic, pin_factory=PiGPIOFactory(address)
        )
    except (ValueError, IndexError, KeyError):
        return None


def write_output(switch, value):
    """Write a value to a GPIO."""
    if value == 1:
        switch.on()
    if value == 0:
        switch.off()
