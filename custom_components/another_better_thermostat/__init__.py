"""The another:better_thermostat component."""
import logging
from asyncio import Lock

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Config, HomeAssistant
from utils.const import DOMAIN,LOGGER

PLATFORMS = [Platform.CLIMATE]
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

config_entry_update_listener_lock = Lock()
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, _config: Config)->bool:
    """Set up this integration using YAML is not supported."""
    _LOGGER.debug("async_setup")
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle setup entry."""
    _LOGGER.debug("async_setup_entry")
    hass.data[DOMAIN] = {}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    async with config_entry_update_listener_lock:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass:HomeAssistant, entry:ConfigEntry)->any:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:  # noqa: D103
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
