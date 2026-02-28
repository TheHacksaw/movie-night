"""Base entity for the Movie Night integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MovieNightCoordinator


class MovieNightEntity(CoordinatorEntity[MovieNightCoordinator]):
    """Base entity for Movie Night."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MovieNightCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Movie Night",
            manufacturer="TMDB",
            model="Netflix Catalog Browser",
            sw_version="1.0.0",
        )
