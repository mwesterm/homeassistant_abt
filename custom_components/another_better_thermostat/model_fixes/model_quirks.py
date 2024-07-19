import logging  # noqa: D100
from importlib import import_module

_LOGGER = logging.getLogger(__name__)


def load_model_quirks(self, model, entity_id):  # noqa: ANN001, ANN201
    """Load model."""
    # remove / from model
    model = model.replace("/", "_")

    try:
        self.model_quirks = import_module(
            "custom_components.another_better_thermostat.model_fixes." + model,
            package="better_thermostat",
        )
        _LOGGER.debug(
            "better_thermostat %s: uses quirks fixes for model %s for trv %s",
            self.name,
            model,
            entity_id,
        )
    except Exception:  # noqa: BLE001
        self.model_quirks = import_module(
            "custom_components.better_thermostat.model_fixes.default",
            package="better_thermostat",
        )

    return self.model_quirks


def fix_local_calibration(self, entity_id, offset):  # noqa: ANN001, ANN201
    """
    Modifies the input local calibration offset, based on the TRV's model quirks,
    to achieve the desired heating behavior.

    Returns
    -------
    float
          new local calibration offset, if the TRV model has any quirks/fixes.
    """  # noqa: D205, D401, D413
    _new_offset = self.real_trvs[entity_id]["model_quirks"].fix_local_calibration(
        self, entity_id, offset
    )

    if offset != _new_offset:
        _LOGGER.debug(
            "better_thermostat %s: %s - calibration offset model fix: %s to %s",
            self.name,
            entity_id,
            offset,
            _new_offset,
        )

    return _new_offset


def fix_target_temperature_calibration(self, entity_id, temperature):  # noqa: ANN001, ANN201
    """
    Modifies the input setpoint temperature, based on the TRV's model quirks,
    to achieve the desired heating behavior.

    Returns
    -------
    float
          new setpoint temperature, if the TRV model has any quirks/fixes.

    """  # noqa: D205, D401
    _new_temperature = self.real_trvs[entity_id][
        "model_quirks"
    ].fix_target_temperature_calibration(self, entity_id, temperature)

    if temperature != _new_temperature:
        _LOGGER.debug(
            "better_thermostat %s: %s - temperature offset model fix: %s to %s",
            self.name,
            entity_id,
            temperature,
            _new_temperature,
        )

    return _new_temperature


async def override_set_hvac_mode(self, entity_id, hvac_mode):  # noqa: ANN001, ANN201, D103
    return await self.real_trvs[entity_id]["model_quirks"].override_set_hvac_mode(
        self, entity_id, hvac_mode
    )


async def override_set_temperature(self, entity_id, temperature):# noqa: ANN001, ANN201, D103
    return await self.real_trvs[entity_id]["model_quirks"].override_set_temperature(
        self, entity_id, temperature
    )
