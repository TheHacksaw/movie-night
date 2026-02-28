"""Camera entity for the Movie Night integration.

Serves a composite "Now Playing" poster image that can be:
- Displayed in Lovelace dashboards via picture-entity card
- Cast to any media_player (Chromecast, smart TV, Apple TV) via play_media
"""

from __future__ import annotations

import logging

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MovieNightCoordinator
from .entity import MovieNightEntity
from .image_generator import generate_idle_image, generate_poster
from .tmdb_client import TMDBClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Movie Night camera."""
    coordinator: MovieNightCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MovieNightCamera(hass, coordinator)])


class MovieNightCamera(MovieNightEntity, Camera):
    """Camera entity serving the 'Now Playing' composite poster image."""

    _attr_name = "Poster"
    _attr_icon = "mdi:image-frame"

    def __init__(
        self, hass: HomeAssistant, coordinator: MovieNightCoordinator
    ) -> None:
        """Initialize the camera."""
        MovieNightEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._hass = hass
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_poster_camera"
        self._cached_image: bytes | None = None
        self._cached_title_id: int | None = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the current poster image."""
        title = self.coordinator.selected_title

        if title is None:
            # Generate or return cached idle image
            if self._cached_image is not None and self._cached_title_id is None:
                return self._cached_image
            self._cached_image = await generate_idle_image(self._hass)
            self._cached_title_id = None
            return self._cached_image

        # Check if we need to regenerate
        current_id = title.get("id")
        if self._cached_image is not None and self._cached_title_id == current_id:
            return self._cached_image

        # Generate new poster image
        content_type = title.get("content_type", "movie")
        title_name = title.get("title") or title.get("name") or "Unknown"
        year = (
            title.get("release_date", "")[:4]
            or title.get("first_air_date", "")[:4]
        )
        rating = title.get("vote_average")
        overview = title.get("overview", "")

        genre_names = self.coordinator.resolve_genre_names(
            title.get("genre_ids", []) or [],
            content_type,
        )
        if not genre_names and "genres" in title:
            genre_names = [g.get("name", "") for g in title.get("genres", [])]
        genres = ", ".join(genre_names)

        poster_url = TMDBClient.poster_url(title.get("poster_path"))
        backdrop_url = TMDBClient.backdrop_url(title.get("backdrop_path"))

        try:
            self._cached_image = await generate_poster(
                self._hass,
                title_name,
                year,
                rating,
                genres,
                overview,
                poster_url,
                backdrop_url,
            )
            self._cached_title_id = current_id
        except Exception:
            _LOGGER.exception("Failed to generate poster image")
            self._cached_image = await generate_idle_image(self._hass)
            self._cached_title_id = None

        return self._cached_image

    @property
    def is_on(self) -> bool:
        """Return True if a title is selected."""
        return self.coordinator.selected_title is not None
