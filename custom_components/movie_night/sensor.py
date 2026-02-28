"""Sensor entity for the Movie Night integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MovieNightCoordinator
from .entity import MovieNightEntity
from .tmdb_client import TMDBClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Movie Night sensor."""
    coordinator: MovieNightCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MovieNightSensor(coordinator)])


class MovieNightSensor(MovieNightEntity, SensorEntity):
    """Sensor showing the currently selected title."""

    _attr_name = "Now Playing"
    _attr_icon = "mdi:movie-open"

    def __init__(self, coordinator: MovieNightCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_now_playing"

    @property
    def native_value(self) -> str:
        """Return the title of the currently selected media, or 'Idle'."""
        title = self.coordinator.selected_title
        if title is None:
            return "Idle"
        return title.get("title") or title.get("name") or "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes about the selected title."""
        title = self.coordinator.selected_title
        if title is None:
            return {}

        content_type = title.get("content_type", "movie")
        year = (
            title.get("release_date", "")[:4]
            or title.get("first_air_date", "")[:4]
        )
        genre_names = self.coordinator.resolve_genre_names(
            title.get("genre_ids", []) or [],
            content_type,
        )
        if not genre_names and "genres" in title:
            genre_names = [g.get("name", "") for g in title.get("genres", [])]

        return {
            "tmdb_id": title.get("id"),
            "content_type": content_type,
            "year": year,
            "rating": title.get("vote_average"),
            "overview": title.get("overview"),
            "genres": ", ".join(genre_names),
            "poster_url": TMDBClient.poster_url(title.get("poster_path")),
            "backdrop_url": TMDBClient.backdrop_url(title.get("backdrop_path")),
        }

    @property
    def entity_picture(self) -> str | None:
        """Return the poster as the entity picture."""
        title = self.coordinator.selected_title
        if title is None:
            return None
        return TMDBClient.poster_url(title.get("poster_path"))
