"""Media player entity for the Movie Night integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .browse_media import async_browse_media
from .const import DOMAIN
from .coordinator import MovieNightCoordinator
from .entity import MovieNightEntity
from .tmdb_client import TMDBClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Movie Night media player."""
    coordinator: MovieNightCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MovieNightMediaPlayer(coordinator)])


class MovieNightMediaPlayer(MovieNightEntity, MediaPlayerEntity):
    """Media player entity for Movie Night."""

    _attr_name = "Player"
    _attr_supported_features = (
        MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.STOP
    )
    _attr_media_image_remotely_accessible = True

    def __init__(self, coordinator: MovieNightCoordinator) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_media_player"

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the media player."""
        if self.coordinator.selected_title is not None:
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def media_title(self) -> str | None:
        """Return the title of the currently selected media."""
        title = self.coordinator.selected_title
        if title is None:
            return None
        return title.get("title") or title.get("name")

    @property
    def media_content_type(self) -> MediaType | str | None:
        """Return the content type of the currently selected media."""
        title = self.coordinator.selected_title
        if title is None:
            return None
        content_type = title.get("content_type", "movie")
        return MediaType.MOVIE if content_type == "movie" else MediaType.TVSHOW

    @property
    def entity_picture(self) -> str | None:
        """Return the poster image URL."""
        title = self.coordinator.selected_title
        if title is None:
            return None
        return TMDBClient.poster_url(title.get("poster_path"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for the selected title."""
        title = self.coordinator.selected_title
        if title is None:
            return {}

        content_type = title.get("content_type", "movie")
        year = (
            title.get("release_date", "")[:4]
            or title.get("first_air_date", "")[:4]
        )
        genre_names = self.coordinator.resolve_genre_names(
            title.get("genre_ids", []) or title.get("genres_ids", []),
            content_type,
        )
        # If detailed data has 'genres' as list of dicts
        if not genre_names and "genres" in title:
            genre_names = [g.get("name", "") for g in title.get("genres", [])]

        return {
            "tmdb_id": title.get("id"),
            "content_type": content_type,
            "year": year,
            "rating": title.get("vote_average"),
            "overview": title.get("overview"),
            "genres": ", ".join(genre_names),
            "backdrop_url": TMDBClient.backdrop_url(title.get("backdrop_path")),
            "poster_url": TMDBClient.poster_url(title.get("poster_path")),
            "netflix_url": f"https://www.netflix.com/title/{title.get('id', '')}",
        }

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Implement the media browser."""
        return await async_browse_media(
            self.coordinator, media_content_type, media_content_id
        )

    async def async_play_media(
        self,
        media_type: MediaType | str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Select a title from the media browser."""
        # Parse media_id: "netflix/movie/12345" or "netflix/tv/67890"
        parts = media_id.split("/")
        if len(parts) != 3 or parts[0] != "netflix":
            _LOGGER.error("Invalid media_id format: %s", media_id)
            return

        content_type = parts[1]
        tmdb_id = int(parts[2])

        # Fetch full details from TMDB
        if content_type == "movie":
            details = await self.coordinator.client.get_movie_details(tmdb_id)
        else:
            details = await self.coordinator.client.get_tv_details(tmdb_id)

        details["content_type"] = content_type
        self.coordinator.select_title(details)

    async def async_media_stop(self) -> None:
        """Clear the current selection."""
        self.coordinator.clear_selection()
