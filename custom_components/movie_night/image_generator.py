"""Poster image generator for the Movie Night integration.

Composites a clean "Now Playing" image using Pillow with:
- TMDB backdrop as full-bleed background with dark overlay
- Movie poster centred with a subtle drop shadow
- No text — designed to look great on a large TV
"""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageDraw, ImageFilter

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import POSTER_HEIGHT, POSTER_WIDTH

_LOGGER = logging.getLogger(__name__)

# Centred poster — fills most of the canvas height
POSTER_DISPLAY_HEIGHT = 820
# Shadow
SHADOW_OFFSET = 10
SHADOW_BLUR = 18


async def _download_image(
    hass: HomeAssistant, url: str
) -> Image.Image | None:
    """Download an image from a URL and return a PIL Image."""
    try:
        session = async_get_clientsession(hass)
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()
            return Image.open(io.BytesIO(data))
    except Exception:
        _LOGGER.debug("Failed to download image: %s", url, exc_info=True)
        return None


def _generate_poster_image(
    backdrop: Image.Image | None,
    poster: Image.Image | None,
) -> bytes:
    """Generate the composite poster image (CPU-bound, run in executor).

    Layout: full-bleed backdrop with dark overlay, movie poster centred.
    """
    canvas = Image.new("RGB", (POSTER_WIDTH, POSTER_HEIGHT), (15, 15, 15))

    # ── Backdrop ──────────────────────────────────────────────────────
    if backdrop:
        backdrop_resized = backdrop.resize(
            (POSTER_WIDTH, POSTER_HEIGHT), Image.Resampling.LANCZOS
        )
        # Heavier blur so the poster stands out
        backdrop_resized = backdrop_resized.filter(
            ImageFilter.GaussianBlur(radius=8)
        )
        canvas.paste(backdrop_resized, (0, 0))

        # Semi-transparent dark overlay to push the backdrop back
        overlay = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0, 0, 0, 150))
        canvas = Image.alpha_composite(
            canvas.convert("RGBA"), overlay
        ).convert("RGB")

    # ── Centred movie poster with drop shadow ─────────────────────────
    if poster:
        # Scale poster to target height while preserving aspect ratio
        aspect = poster.width / poster.height
        poster_h = min(POSTER_DISPLAY_HEIGHT, POSTER_HEIGHT - 130)
        poster_w = int(poster_h * aspect)

        poster_resized = poster.resize(
            (poster_w, poster_h), Image.Resampling.LANCZOS
        )

        # Centre position
        paste_x = (POSTER_WIDTH - poster_w) // 2
        paste_y = (POSTER_HEIGHT - poster_h) // 2

        # Draw soft drop shadow behind the poster
        shadow_pad = 40
        shadow = Image.new(
            "RGBA",
            (poster_w + shadow_pad * 2, poster_h + shadow_pad * 2),
            (0, 0, 0, 0),
        )
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            [shadow_pad, shadow_pad, poster_w + shadow_pad, poster_h + shadow_pad],
            radius=12,
            fill=(0, 0, 0, 180),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR))

        shadow_canvas = Image.new(
            "RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0, 0, 0, 0)
        )
        shadow_canvas.paste(
            shadow,
            (paste_x - shadow_pad + SHADOW_OFFSET, paste_y - shadow_pad + SHADOW_OFFSET),
        )
        canvas = Image.alpha_composite(
            canvas.convert("RGBA"), shadow_canvas
        ).convert("RGB")

        # Paste poster with rounded corners
        mask = Image.new("L", (poster_w, poster_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [0, 0, poster_w, poster_h], radius=10, fill=255
        )
        canvas.paste(poster_resized, (paste_x, paste_y), mask)

    # ── Encode ────────────────────────────────────────────────────────
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def generate_poster(
    hass: HomeAssistant,
    title: str,
    year: str,
    rating: float | None,
    genres: str,
    overview: str,
    poster_url: str | None,
    backdrop_url: str | None,
) -> bytes:
    """Generate a composite 'Now Playing' poster image.

    Downloads images from TMDB and composites them.
    The CPU-bound Pillow work runs in an executor.
    """
    backdrop = None
    poster = None

    if backdrop_url:
        backdrop = await _download_image(hass, backdrop_url)
    if poster_url:
        poster = await _download_image(hass, poster_url)

    return await hass.async_add_executor_job(
        _generate_poster_image,
        backdrop,
        poster,
    )


async def generate_idle_image(hass: HomeAssistant) -> bytes:
    """Generate a default idle state image."""
    return await hass.async_add_executor_job(_generate_idle_image_sync)


def _generate_idle_image_sync() -> bytes:
    """Generate a simple dark idle state image (CPU-bound)."""
    canvas = Image.new("RGB", (POSTER_WIDTH, POSTER_HEIGHT), (15, 15, 15))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
