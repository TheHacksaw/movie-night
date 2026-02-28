"""DataUpdateCoordinator for the Movie Night integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_API_KEY,
    CONF_COUNTRY,
    CONF_POLL_INTERVAL,
    DEFAULT_CATALOG_PAGES,
    DEFAULT_COUNTRY,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)
from .tmdb_client import TMDBClient

_LOGGER = logging.getLogger(__name__)


class MovieNightCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage TMDB data fetching and selected title state."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: TMDBClient,
    ) -> None:
        """Initialize the coordinator."""
        poll_hours = config_entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=poll_hours),
            config_entry=config_entry,
        )
        self.client = client
        self.genres: dict[str, dict[int, str]] = {}
        self._selected_title: dict[str, Any] | None = None

    @property
    def country(self) -> str:
        """Get the configured country code."""
        return self.config_entry.options.get(
            CONF_COUNTRY,
            self.config_entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY),
        )

    @property
    def selected_title(self) -> dict[str, Any] | None:
        """Get the currently selected title."""
        return self._selected_title

    def select_title(self, title_data: dict[str, Any]) -> None:
        """Set the currently selected title and notify listeners."""
        self._selected_title = title_data
        self.async_set_updated_data(self.data)

    def clear_selection(self) -> None:
        """Clear the currently selected title and notify listeners."""
        self._selected_title = None
        self.async_set_updated_data(self.data)

    async def _async_setup(self) -> None:
        """Fetch genre lists on first coordinator setup (called once)."""
        try:
            self.genres = await self.client.get_genres()
            _LOGGER.debug(
                "Loaded %d movie genres, %d TV genres",
                len(self.genres.get("movie", {})),
                len(self.genres.get("tv", {})),
            )
        except ConnectionError as err:
            _LOGGER.warning("Failed to fetch genres: %s", err)
            self.genres = {"movie": {}, "tv": {}}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch popular Netflix content from TMDB."""
        country = self.country
        movies: list[dict] = []
        tv_shows: list[dict] = []

        try:
            for page in range(1, DEFAULT_CATALOG_PAGES + 1):
                movie_data = await self.client.get_netflix_movies(country, page)
                movies.extend(movie_data.get("results", []))

                tv_data = await self.client.get_netflix_tv(country, page)
                tv_shows.extend(tv_data.get("results", []))

        except ConnectionError as err:
            raise UpdateFailed(f"Failed to fetch Netflix catalog: {err}") from err

        _LOGGER.debug(
            "Fetched %d movies and %d TV shows for %s",
            len(movies),
            len(tv_shows),
            country,
        )

        return {
            "movies": movies,
            "tv": tv_shows,
            "genres": self.genres,
        }

    def resolve_genre_names(
        self, genre_ids: list[int], content_type: str
    ) -> list[str]:
        """Resolve genre IDs to genre names."""
        genre_map = self.genres.get(content_type, {})
        return [genre_map[gid] for gid in genre_ids if gid in genre_map]
