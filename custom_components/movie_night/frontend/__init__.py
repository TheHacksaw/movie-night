"""Frontend registration for Movie Night custom Lovelace cards."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, URL_BASE

_LOGGER = logging.getLogger(__name__)

# Cards to register
CARDS = [
    "movie-night-poster.js",
    "movie-night-browser.js",
]

_REGISTERED = False


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the frontend static paths and Lovelace resources."""
    global _REGISTERED
    if _REGISTERED:
        return
    _REGISTERED = True

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

    # Load each card JS file on every page via add_extra_js_url.
    # This ensures the custom elements are defined and appear in
    # the Lovelace card picker.
    for card_file in CARDS:
        add_extra_js_url(hass, f"{URL_BASE}/{card_file}")

    _LOGGER.debug("Movie Night frontend resources registered")
