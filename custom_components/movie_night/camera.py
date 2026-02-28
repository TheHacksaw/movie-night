"""Camera entity for the Movie Night integration.

Serves a composite "Now Playing" poster image that can be:
- Displayed in Lovelace dashboards via picture-entity card
- Cast to any media_player (Chromecast, smart TV, Apple TV) via play_media
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BACKDROP_SIZE_ORIGINAL, DOMAIN, POSTER_SIZE_LARGE, URL_BASE
from .coordinator import MovieNightCoordinator
from .entity import MovieNightEntity
from .image_generator import generate_idle_image, generate_poster
from .tmdb_client import TMDBClient

_LOGGER = logging.getLogger(__name__)

# Image filename — served at /movie-night/poster.png (no auth required)
PUBLIC_IMAGE_FILENAME = "poster.png"


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

        # Save the poster into the frontend directory which is already
        # registered as a static path at /movie-night/ — no auth required.
        self._static_dir = Path(__file__).parent / "frontend"
        self._static_dir.mkdir(exist_ok=True)
        self._public_image_path = self._static_dir / PUBLIC_IMAGE_FILENAME

        # Also save a copy to /config/www/ as a fallback
        self._www_dir = Path(hass.config.path("www"))
        self._www_dir.mkdir(exist_ok=True)
        self._www_image_path = self._www_dir / "movie_night_poster.png"

    async def async_added_to_hass(self) -> None:
        """Generate the initial idle image as soon as the entity is registered."""
        await super().async_added_to_hass()
        await self._regenerate_image()

    def _handle_coordinator_update(self) -> None:
        """Proactively regenerate the image whenever the coordinator updates."""
        super()._handle_coordinator_update()
        self._hass.async_create_task(self._regenerate_image())

    async def _regenerate_image(self) -> None:
        """Regenerate the poster image and save to the static path."""
        title = self.coordinator.selected_title

        if title is None:
            if self._cached_image is not None and self._cached_title_id is None:
                return  # already have idle image cached
            self._cached_image = await generate_idle_image(self._hass)
            self._cached_title_id = None
            await self._save_public_image(self._cached_image)
            return

        current_id = title.get("id")
        if self._cached_image is not None and self._cached_title_id == current_id:
            return  # same title, no regeneration needed

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

        poster_url = TMDBClient.poster_url(title.get("poster_path"), POSTER_SIZE_LARGE)
        backdrop_url = TMDBClient.backdrop_url(title.get("backdrop_path"), BACKDROP_SIZE_ORIGINAL)

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

        await self._save_public_image(self._cached_image)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the current poster image."""
        if self._cached_image is None:
            await self._regenerate_image()
        return self._cached_image

    async def _save_public_image(self, image_data: bytes) -> None:
        """Save the poster image to both static locations for unauthenticated access.

        Primary:  http://<HA_IP>:8123/movie-night/poster.png
                  (uses the same static path already registered for the JS cards)
        Fallback: http://<HA_IP>:8123/local/movie_night_poster.png
                  (standard /config/www/ directory)
        """
        try:
            await self._hass.async_add_executor_job(
                self._write_both, image_data
            )
        except Exception:
            _LOGGER.debug("Failed to save public poster image", exc_info=True)

    def _write_both(self, image_data: bytes) -> None:
        """Write image data to both locations (runs in executor)."""
        self._public_image_path.write_bytes(image_data)
        try:
            self._www_image_path.write_bytes(image_data)
        except Exception:
            pass  # /config/www/ is a fallback, don't fail if it doesn't work

    @property
    def is_on(self) -> bool:
        """Return True if a title is selected."""
        return self.coordinator.selected_title is not None
