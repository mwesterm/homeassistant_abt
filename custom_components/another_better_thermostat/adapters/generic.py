# ruff: noqa: ANN001  # noqa: D100
# ruff: noqa: ANN201
import asyncio
import logging

from homeassistant.components.number.const import SERVICE_SET_VALUE
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.another_better_thermostat.utils.helpers import (
    find_local_calibration_entity,
)

_LOGGER = logging.getLogger(__name__)


async def get_info(self, entity_id):
    """Get info from TRV."""
    support_offset = False

    offset = await find_local_calibration_entity(self, entity_id)
    if offset is not None:
        support_offset = True
    return {"support_offset": support_offset, "support_valve": False}


async def init(self, entity_id):  # noqa: D103
    if (
        self.real_trvs[entity_id]["local_temperature_calibration_entity"] is None
        and self.real_trvs[entity_id]["calibration"] != 1
    ):
        self.real_trvs[entity_id]["local_temperature_calibration_entity"] = (
            await find_local_calibration_entity(self, entity_id)
        )
        _LOGGER.debug(
            "better_thermostat %s: uses local calibration entity %s",
            self.name,
            self.real_trvs[entity_id]["local_temperature_calibration_entity"],
        )
        # Wait for the entity to be available
        _ready = True
        while _ready:
            if self.hass.states.get(
                self.real_trvs[entity_id]["local_temperature_calibration_entity"]
            ).state in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
                _LOGGER.info(
                    "better_thermostat %s: waiting for TRV/climate entity with id '%s' to become fully available...",  # noqa: E501
                    self.name,
                    self.real_trvs[entity_id]["local_temperature_calibration_entity"],
                )
                await asyncio.sleep(5)
                continue
            _ready = False
            return

    return


async def get_current_offset(self, entity_id):
    """Get current offset."""
    if self.real_trvs[entity_id]["local_temperature_calibration_entity"] is not None:
        return float(
            str(
                self.hass.states.get(
                    self.real_trvs[entity_id]["local_temperature_calibration_entity"]
                ).state
            )
        )
    return None


async def get_offset_steps(self, entity_id):
    """Get offset steps."""
    if self.real_trvs[entity_id]["local_temperature_calibration_entity"] is not None:
        return float(
            str(
                self.hass.states.get(
                    self.real_trvs[entity_id]["local_temperature_calibration_entity"]
                ).attributes.get("step", 1)
            )
        )
    return None


async def get_min_offset(self, entity_id):
    """Get min offset."""
    if self.real_trvs[entity_id]["local_temperature_calibration_entity"] is not None:
        return float(
            str(
                self.hass.states.get(
                    self.real_trvs[entity_id]["local_temperature_calibration_entity"]
                ).attributes.get("min", -10)
            )
        )
    return -6


async def get_max_offset(self, entity_id):
    """Get max offset."""
    if self.real_trvs[entity_id]["local_temperature_calibration_entity"] is not None:
        return float(
            str(
                self.hass.states.get(
                    self.real_trvs[entity_id]["local_temperature_calibration_entity"]
                ).attributes.get("max", 10)
            )
        )
    return 6


async def set_temperature(self, entity_id, temperature):
    """Set new target temperature."""
    await self.hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": entity_id, "temperature": temperature},
        blocking=True,
        context=self.context,
    )


async def set_hvac_mode(self, entity_id, hvac_mode):
    """Set new target hvac mode."""
    _LOGGER.debug("better_thermostat %s: set_hvac_mode %s", self.name, hvac_mode)
    try:
        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": entity_id, "hvac_mode": hvac_mode},
            blocking=True,
            context=self.context,
        )
    except TypeError:
        _LOGGER.debug("TypeError in set_hvac_mode")


async def set_offset(self, entity_id, offset):
    """Set new target offset."""
    if self.real_trvs[entity_id]["local_temperature_calibration_entity"] is not None:
        max_calibration = await get_max_offset(self, entity_id)
        min_calibration = await get_min_offset(self, entity_id)

        if offset >= max_calibration:
            offset = max_calibration
        if offset <= min_calibration:
            offset = min_calibration

        await self.hass.services.async_call(
            "number",
            SERVICE_SET_VALUE,
            {
                "entity_id": self.real_trvs[entity_id][
                    "local_temperature_calibration_entity"
                ],
                "value": offset,
            },
            blocking=True,
            context=self.context,
        )
        self.real_trvs[entity_id]["last_calibration"] = offset
        if (
            self.real_trvs[entity_id]["last_hvac_mode"] is not None
            and self.real_trvs[entity_id]["last_hvac_mode"] != "off"
        ):
            await asyncio.sleep(3)
            await set_hvac_mode(
                self, entity_id, self.real_trvs[entity_id]["last_hvac_mode"]
            )

        return offset
    return None  # Not supported


async def set_valve(self, entity_id, valve)->None:  # noqa: ARG001
    """Set new target valve."""
    return  # Not supported
