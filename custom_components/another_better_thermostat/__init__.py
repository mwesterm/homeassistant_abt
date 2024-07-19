"""The another_better_thermostat component."""
import asyncio
from asyncio import Lock

# import voluptuous as vol # noqa: ERA001
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Config, HomeAssistant

from custom_components.another_better_thermostat.utils.const import DOMAIN, LOGGER

PLATFORMS = [Platform.CLIMATE]
# CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)  # noqa: E501, ERA001

config_entry_update_listener_lock = Lock()


async def async_setup(hass: HomeAssistant, _config: Config) -> bool:
    """Set up this integration using YAML is not supported."""
    LOGGER.debug("async_setup")
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle setup entry."""
    LOGGER.debug("async_setup_entry")
    hass.data[DOMAIN] = {}

    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    entry.add_update_listener(async_reload_entry)
    return True

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    async with config_entry_update_listener_lock:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:  # noqa: D103
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded
