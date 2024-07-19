# noqa: D100
import asyncio
from abc import ABC
from datetime import datetime, timedelta

from homeassistant.components.climate import (
    PRESET_NONE,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    EVENT_HOMEASSISTANT_START,
)
from homeassistant.core import Context, CoreState, ServiceCall, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.another_better_thermostat.model_fixes.model_quirks import (
    load_model_quirks,
)

from .adapters.delegate import (
    load_adapter,
)
from .utils.const import (
    ANOTHER_BETTERTHERMOSTAT_SET_TEMPERATURE_SCHEMA,
    CONF_HEATER,
    CONF_MODEL,
    CONF_OFF_TEMPERATURE,
    CONF_SENSOR,
    CONF_TARGET_TEMP_STEP,
    CONF_TOLERANCE,
    DOMAIN,
    LOGGER,
    SERVICE_RESET_HEATING_POWER,
    SERVICE_RESTORE_SAVED_TARGET_TEMPERATURE,
    SERVICE_SET_TEMP_TARGET_TEMPERATURE,
    SUPPORT_FLAGS,
    VERSION,
    AnotherBetterThermostatEntityFeature,
)
from .utils.controlling import control_queue


async def async_setup_entry(hass, entry, async_add_devices) -> None:  # noqa: ANN001
    """Setup sensor platform."""  # noqa: D401

    async def async_service_handler(self, data: ServiceCall) -> None:  # noqa: ANN001
        LOGGER.debug("Service call: %s  » %s", self, data.service)
        if data.service == SERVICE_RESTORE_SAVED_TARGET_TEMPERATURE:
            await self.restore_temp_temperature()
        elif data.service == SERVICE_SET_TEMP_TARGET_TEMPERATURE:
            await self.set_temp_temperature(data.data[ATTR_TEMPERATURE])
        elif data.service == SERVICE_RESET_HEATING_POWER:
            await self.reset_heating_power()

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_TEMP_TARGET_TEMPERATURE,
        ANOTHER_BETTERTHERMOSTAT_SET_TEMPERATURE_SCHEMA,
        async_service_handler,
        [
            AnotherBetterThermostatEntityFeature.TARGET_TEMPERATURE,
            AnotherBetterThermostatEntityFeature.TARGET_TEMPERATURE_RANGE,
        ],
    )
    platform.async_register_entity_service(
        SERVICE_RESTORE_SAVED_TARGET_TEMPERATURE, {}, async_service_handler
    )
    platform.async_register_entity_service(
        SERVICE_RESET_HEATING_POWER, {}, async_service_handler
    )
    async_add_devices(
        [
            AnotherBetterThermostat(
                name=entry.data.get(CONF_NAME),
                heater_entity_id=entry.data.get(CONF_HEATER),
                sensor_entity_id=entry.data.get(CONF_SENSOR),
                off_temperature=entry.data.get(CONF_OFF_TEMPERATURE, None),
                tolerance=entry.data.get(CONF_TOLERANCE, 0.0),
                target_temp_step=entry.data.get(CONF_TARGET_TEMP_STEP, "0.0"),
                model=entry.data.get(CONF_MODEL, None),
                unit=hass.config.units.temperature_unit,
                unique_id=entry.entry_id,
                device_class="another_better_thermostat",
                state_class="another_better_thermostat_state",
            )
        ]
    )


class AnotherBetterThermostat(ClimateEntity, RestoreEntity, ABC):
    """Representation of a Better Thermostat device."""

    @property
    def device_info(self) -> dict:  # noqa: D102
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.device_name,
            "manufacturer": "Better Thermostat",
            "model": self.model,
            "sw_version": VERSION,
        }

    def __init__(  # noqa: D417, PLR0913, PLR0915
        self,
        name,  # noqa: ANN001
        heater_entity_id,  # noqa: ANN001
        sensor_entity_id,  # noqa: ANN001
        off_temperature,  # noqa: ANN001
        tolerance,  # noqa: ANN001
        target_temp_step,  # noqa: ANN001
        model,  # noqa: ANN001
        unit: str,
        unique_id,  # noqa: ANN001
        device_class: str,
        state_class: str,
    ) -> None:
        """
        Initialize the thermostat.

        Parameters
        ----------
        self,
        name,
        heater_entity_id,
        sensor_entity_id,
        off_temperature,
        tolerance,
        target_temp_step,
        model,
        unit: str,
        unique_id,
        device_class: str,
        state_class: str,

        """
        self.device_name = name
        self.model = model
        self.real_trvs = {}
        self.entity_ids = []
        self.all_trvs = heater_entity_id
        self.sensor_entity_id = sensor_entity_id
        self.off_temperature = float(off_temperature) or None
        self.tolerance = float(tolerance) or 0.0
        self._unique_id = unique_id
        self._unit = unit
        self._device_class = device_class
        self._state_class = state_class
        self._hvac_list = [HVACMode.HEAT, HVACMode.OFF]
        self._preset_mode = PRESET_NONE
        self.map_on_hvac_mode = HVACMode.HEAT
        self.cur_temp = None
        self.cur_humidity = 0
        self.bt_target_temp_step = float(target_temp_step) or 0.0
        self.bt_min_temp = 0
        self.bt_max_temp = 30
        self.bt_target_temp = 5.0
        self._support_flags = SUPPORT_FLAGS | ClimateEntityFeature.PRESET_MODE
        self.bt_hvac_mode = None
        self.call_for_heat = True
        self.ignore_states = False
        self.last_dampening_timestamp = None
        self.version = VERSION
        self.last_change = datetime.now() - timedelta(hours=2)  # noqa: DTZ005
        self.last_external_sensor_change = datetime.now() - timedelta(hours=2)  # noqa: DTZ005
        self.last_internal_sensor_change = datetime.now() - timedelta(hours=2)  # noqa: DTZ005
        self._temp_lock = asyncio.Lock()
        self.startup_running = True
        self._saved_temperature = None
        self.last_avg_outdoor_temp = None
        self.last_main_hvac_mode = None
        self.last_window_state = None
        self._last_call_for_heat = None
        self._available = False
        self.context = None
        self.attr_hvac_action = None
        self.old_attr_hvac_action = None
        self.heating_start_temp = None
        self.heating_start_timestamp = None
        self.heating_end_temp = None
        self.heating_end_timestamp = None
        self._async_unsub_state_changed = None
        self.all_entities = []
        self.devices_states = {}
        self.devices_errors = []
        self.control_queue_task = asyncio.Queue(maxsize=1)
        self.task = asyncio.create_task(control_queue(self))
        self.heating_power = 0.01
        self.last_heating_power_stats = []
        self.is_removed = False

    async def async_added_to_hass(self) -> None:
        """
        Run when entity about to be added.

        Returns
        -------
        None

        """
        LOGGER.debug("Added to hass")
        self.entity_ids = [
            entity for trv in self.all_trvs if (entity := trv["trv"]) is not None
        ]

        for trv in self.all_trvs:
            _calibration = 1
            if trv["advanced"]["calibration"] == "local_calibration_based":
                _calibration = 0
            if trv["advanced"]["calibration"] == "hybrid_calibration":
                _calibration = 2
            _adapter = load_adapter(self, trv["integration"], trv["trv"])
            _model_quirks = load_model_quirks(self, trv["model"], trv["trv"])
            self.real_trvs[trv["trv"]] = {
                "calibration": _calibration,
                "integration": trv["integration"],
                "adapter": _adapter,
                "model_quirks": _model_quirks,
                "model": trv["model"],
                "advanced": trv["advanced"],
                "ignore_trv_states": False,
                "valve_position": None,
                "max_temp": None,
                "min_temp": None,
                "target_temp_step": None,
                "temperature": None,
                "current_temperature": None,
                "hvac_modes": None,
                "hvac_mode": None,
                "local_temperature_calibration_entity": None,
                "local_calibration_min": None,
                "local_calibration_max": None,
                "calibration_received": True,
                "target_temp_received": True,
                "system_mode_received": True,
                "last_temperature": None,
                "last_valve_position": None,
                "last_hvac_mode": None,
                "last_current_temperature": None,
                "last_calibration": None,
            }

        def on_remove() -> None:
            self.is_removed = True

        self.async_on_remove(on_remove)

        await super().async_added_to_hass()

        LOGGER.info(
            "better_thermostat %s: Waiting for entity to be ready...", self.device_name
        )

        @callback
        def _async_startup(*_) -> None:  # noqa: ANN002
            """
            Init on startup.

            Parameters
            ----------
            _ :
                    All parameters are piped.

            """
            self.context = Context()
            loop = asyncio.get_event_loop()
            loop.create_task(self.startup())  # noqa: RUF006

        if self.hass.state == CoreState.running:
            _async_startup()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)
