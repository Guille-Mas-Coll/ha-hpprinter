"""
Support for Blue Iris binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.blueiris/
"""
import sys
import logging
from typing import Optional, Union

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers import device_registry as dr

from homeassistant.helpers.entity import Entity

from .home_assistant import _get_printer
from .const import *

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_SENSOR


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the EdgeOS Binary Sensor."""
    _LOGGER.debug(f"Starting async_setup_entry {CURRENT_DOMAIN}")

    try:
        entry_data = config_entry.data
        name = entry_data.get(CONF_NAME)
        entities = []

        printer = _get_printer(hass, name)

        if printer is not None:
            entities_data = printer.get_entities(CURRENT_DOMAIN)
            for entity_name in entities_data:
                entity_data = entities_data.get(entity_name)

                entity = PrinterSensor(hass, printer.name, entity_data)

                _LOGGER.debug(f"Setup {CURRENT_DOMAIN}: {entity.name} | {entity.unique_id}")

                entities.append(entity)

        printer.set_domain_entities_state(CURRENT_DOMAIN, True)

        async_add_devices(entities, True)
    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"Failed to load {CURRENT_DOMAIN}, error: {ex}, line: {line_number}")


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    entry_data = config_entry.data
    name = entry_data.get(CONF_NAME)

    printer = _get_printer(hass, name)

    if printer is not None:
        printer.set_domain_entities_state(CURRENT_DOMAIN, False)

    return True


class PrinterSensor(Entity):
    """Representation a binary sensor that is updated by HP Printer."""

    def __init__(self, hass, printer_name, entity):
        """Initialize the HP Printer Sensor."""
        self._hass = hass
        self._printer_name = printer_name
        self._entity = entity
        self._remove_dispatcher = None

    @property
    def unique_id(self) -> Optional[str]:
        """Return the name of the node."""
        return f"{DEFAULT_NAME}-{CURRENT_DOMAIN}-{self.name}"

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self.unique_id)
            },
            "name": self.name,
            "manufacturer": MANUFACTURER,
            ENTITY_MODEL: self._entity.get(ENTITY_MODEL)
        }

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._entity.get(ENTITY_NAME)

    @property
    def icon(self) -> Optional[str]:
        """Return the icon of the sensor."""
        return self._entity.get(ENTITY_ICON)

    @property
    def state(self) -> Union[None, str, int, float]:
        """Return the state of the sensor."""
        return self._entity.get(ENTITY_STATE)

    @property
    def device_state_attributes(self):
        """Return true if the sensor is on."""
        return self._entity.get(ENTITY_ATTRIBUTES)

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._remove_dispatcher = async_dispatcher_connect(self._hass, SIGNALS[CURRENT_DOMAIN], self.update_data)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_dispatcher is not None:
            self._remove_dispatcher()

    @callback
    def update_data(self):
        self.hass.async_add_job(self.async_update_data)

    async def async_update_data(self):
        _LOGGER.debug(f"{CURRENT_DOMAIN} update_data: {self.name} | {self.unique_id}")

        printer = _get_printer(self._hass, self._printer_name)
        if printer is not None:
            self._entity = printer.get_entity(CURRENT_DOMAIN, self.name)

            if self._entity is None:
                self._entity = {}
                await self.async_remove()

                dev_id = self.device_info.get("id")
                device_reg = await dr.async_get_registry(self._hass)

                device_reg.async_remove_device(dev_id)
            else:
                self.async_schedule_update_ha_state(True)
