"""Custom types for integration_blueprint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration


type ABTConfigEntry = ConfigEntry[ABTData]


@dataclass
class ABTData:
    """Data for the Blueprint integration."""

    #    client: IntegrationBlueprintApiClient  # noqa: ERA001
    #    coordinator: BlueprintDataUpdateCoordinator  # noqa: ERA001
    integration: Integration
