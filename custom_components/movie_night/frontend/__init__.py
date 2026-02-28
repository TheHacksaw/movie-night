"""Frontend registration for Movie Night custom Lovelace cards."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, URL_BASE

_LOGGER = logging.getLogger(__name__)

# Cards to register
CARDS = [
    "movie-night-poster.js",
    "movie-night-browser.js",
]


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the frontend static paths and Lovelace resources."""
    frontend_dir = Path(__file__).parent

    # Register static path so HA serves the JS files
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=URL_BASE,
                path=str(frontend_dir),
                cache_headers=False,
            )
        ]
    )

    # Register each card as a Lovelace resource
    for card_file in CARDS:
        resource_url = f"{URL_BASE}/{card_file}"
        _register_resource(hass, resource_url)

    _LOGGER.debug("Movie Night frontend resources registered")


def _register_resource(hass: HomeAssistant, url: str) -> None:
    """Register a Lovelace resource if not already registered."""
    # Access the lovelace resources collection
    resources = hass.data.get("lovelace", {})

    # For YAML mode dashboards, resources are managed in configuration.yaml
    # and we can't dynamically add them. Log a message instead.
    if not hasattr(resources, "resources") or resources.resources is None:
        _LOGGER.info(
            "Movie Night: Add this to your Lovelace resources manually: "
            "%s (type: module)",
            url,
        )
        return

    # Check if already registered
    try:
        existing = resources.resources.async_items()
        for item in existing:
            if item.get("url", "") == url:
                return  # Already registered
    except Exception:
        pass

    # Create the resource entry
    try:
        hass.async_create_task(
            resources.resources.async_create_item({"res_type": "module", "url": url})
        )
        _LOGGER.debug("Registered Lovelace resource: %s", url)
    except Exception:
        _LOGGER.warning(
            "Could not auto-register Lovelace resource: %s. "
            "Add it manually in Settings > Dashboards > Resources.",
            url,
        )
