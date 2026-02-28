"""The Movie Night integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_APPLE_TV_ENTITY,
    DOMAIN,
    EVENT_PLAYBACK_STARTED,
)
from .coordinator import MovieNightCoordinator
from .frontend import async_register_frontend
from .tmdb_client import TMDBClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.SENSOR, Platform.CAMERA]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Movie Night integration (services and frontend)."""
    hass.data.setdefault(DOMAIN, {})

    # Register frontend static paths and Lovelace resources
    await async_register_frontend(hass)

    # Services are registered here but require a config entry to function.
    # The handlers check for an active coordinator at runtime.

    async def _get_coordinator() -> MovieNightCoordinator:
        """Get the active coordinator, raising if none exists."""
        entries = hass.data.get(DOMAIN, {})
        for entry_id, coordinator in entries.items():
            if isinstance(coordinator, MovieNightCoordinator):
                return coordinator
        raise ServiceValidationError(
            "Movie Night is not configured. Please add the integration first."
        )

    async def handle_select_title(call: ServiceCall) -> None:
        """Handle the select_title service."""
        coordinator = await _get_coordinator()
        tmdb_id = int(call.data["tmdb_id"])
        content_type = call.data.get("content_type", "movie")

        if content_type == "movie":
            details = await coordinator.client.get_movie_details(tmdb_id)
        else:
            details = await coordinator.client.get_tv_details(tmdb_id)

        details["content_type"] = content_type
        coordinator.select_title(details)

    async def handle_search(call: ServiceCall) -> dict[str, Any]:
        """Handle the search service."""
        coordinator = await _get_coordinator()
        query = call.data["query"]
        results = await coordinator.client.search(query)

        # Filter to only movie and TV results, enrich with poster URLs
        filtered = []
        for item in results.get("results", []):
            media_type = item.get("media_type")
            if media_type not in ("movie", "tv"):
                continue
            filtered.append(
                {
                    "tmdb_id": item.get("id"),
                    "title": item.get("title") or item.get("name"),
                    "content_type": media_type,
                    "year": (
                        item.get("release_date", "")[:4]
                        or item.get("first_air_date", "")[:4]
                    ),
                    "overview": item.get("overview", ""),
                    "rating": item.get("vote_average"),
                    "poster_url": TMDBClient.poster_url(item.get("poster_path")),
                }
            )

        return {"results": filtered, "total": len(filtered)}

    async def handle_start_playback(call: ServiceCall) -> None:
        """Handle the start_playback service."""
        coordinator = await _get_coordinator()

        apple_tv_entity = coordinator.config_entry.options.get(
            CONF_APPLE_TV_ENTITY,
            coordinator.config_entry.data.get(CONF_APPLE_TV_ENTITY),
        )
        if not apple_tv_entity:
            raise ServiceValidationError(
                "No Apple TV entity configured. "
                "Go to Settings > Integrations > Movie Night > Configure "
                "to set an Apple TV entity."
            )

        title = coordinator.selected_title
        if title is None:
            raise ServiceValidationError(
                "No title is currently selected. "
                "Use movie_night.select_title first."
            )

        tmdb_id = title.get("id")
        title_name = title.get("title") or title.get("name") or "Unknown"

        # Tier 1: Try deep link (may not work due to Netflix restrictions)
        try:
            await hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": apple_tv_entity,
                    "media_content_type": "url",
                    "media_content_id": f"nflx://www.netflix.com/title/{tmdb_id}",
                },
                blocking=True,
            )
            _LOGGER.info("Sent Netflix deep link for '%s'", title_name)
        except Exception:
            _LOGGER.debug(
                "Deep link failed, falling back to app launch",
                exc_info=True,
            )
            # Tier 2: Just open the Netflix app
            try:
                await hass.services.async_call(
                    "media_player",
                    "select_source",
                    {
                        "entity_id": apple_tv_entity,
                        "source": "Netflix",
                    },
                    blocking=True,
                )
                _LOGGER.info("Launched Netflix app on %s", apple_tv_entity)
            except Exception:
                _LOGGER.error(
                    "Failed to launch Netflix on %s", apple_tv_entity,
                    exc_info=True,
                )

        # Fire event for automations
        hass.bus.async_fire(
            EVENT_PLAYBACK_STARTED,
            {
                "title": title_name,
                "tmdb_id": tmdb_id,
                "content_type": title.get("content_type", "movie"),
            },
        )

    async def handle_show_poster(call: ServiceCall) -> None:
        """Handle the show_poster service - cast poster to a media player."""
        await _get_coordinator()  # Validate integration is set up

        target_entity = call.data["target_entity"]

        # Build the camera proxy URL for the poster
        camera_entity_id = None
        for state in hass.states.async_all("camera"):
            if state.entity_id.startswith("camera.movie_night"):
                camera_entity_id = state.entity_id
                break

        if camera_entity_id is None:
            raise ServiceValidationError(
                "Movie Night camera entity not found. "
                "The integration may not be fully loaded."
            )

        # Use the HA internal URL for the camera image
        base_url = hass.config.internal_url or hass.config.external_url or ""
        image_url = f"{base_url}/api/camera_proxy/{camera_entity_id}"

        try:
            await hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": target_entity,
                    "media_content_type": "image/png",
                    "media_content_id": image_url,
                },
                blocking=True,
            )
            _LOGGER.info("Cast poster to %s", target_entity)
        except Exception:
            _LOGGER.error(
                "Failed to cast poster to %s", target_entity,
                exc_info=True,
            )
            raise ServiceValidationError(
                f"Failed to cast poster image to {target_entity}. "
                "Make sure the media player supports displaying images."
            )

    async def handle_clear(call: ServiceCall) -> None:
        """Handle the clear service."""
        coordinator = await _get_coordinator()
        coordinator.clear_selection()

    # Register services
    hass.services.async_register(
        DOMAIN,
        "select_title",
        handle_select_title,
        schema=vol.Schema(
            {
                vol.Required("tmdb_id"): str,
                vol.Optional("content_type", default="movie"): vol.In(
                    ["movie", "tv"]
                ),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        "search",
        handle_search,
        schema=vol.Schema(
            {
                vol.Required("query"): str,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        "start_playback",
        handle_start_playback,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        "show_poster",
        handle_show_poster,
        schema=vol.Schema(
            {
                vol.Required("target_entity"): str,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        "clear",
        handle_clear,
        schema=vol.Schema({}),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Movie Night from a config entry."""
    session = async_get_clientsession(hass)
    client = TMDBClient(session, entry.data[CONF_API_KEY])

    coordinator = MovieNightCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
