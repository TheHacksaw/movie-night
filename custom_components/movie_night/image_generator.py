"""Poster image generator for the Movie Night integration.

Composites a styled "Now Playing" image using Pillow with:
- TMDB backdrop as full background
- Dark gradient overlay
- Movie poster on the left
- Title, year, rating, genres as text
- "NOW PLAYING" badge
"""

from __future__ import annotations

import io
import logging
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import POSTER_HEIGHT, POSTER_WIDTH

_LOGGER = logging.getLogger(__name__)

# Layout constants — sized for legibility on a 55" TV at 8–10 ft viewing distance
POSTER_LEFT_MARGIN = 60
POSTER_TOP_MARGIN = 130
POSTER_DISPLAY_WIDTH = 460
BADGE_HEIGHT = 60
BADGE_TOP = 45


def _load_default_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font, falling back to the default bitmap font."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        except (OSError, IOError):
            try:
                return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
            except (OSError, IOError):
                return ImageFont.load_default()


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
    title: str,
    year: str,
    rating: float | None,
    genres: str,
    overview: str,
) -> bytes:
    """Generate the composite poster image (CPU-bound, run in executor)."""
    canvas = Image.new("RGB", (POSTER_WIDTH, POSTER_HEIGHT), (15, 15, 15))
    draw = ImageDraw.Draw(canvas)

    # Load fonts — large enough to read on a 55" TV from 8–10 ft
    font_title = _load_default_font(76)
    font_meta = _load_default_font(42)
    font_overview = _load_default_font(32)
    font_badge = _load_default_font(34)

    # Draw backdrop with dark overlay
    if backdrop:
        backdrop_resized = backdrop.resize(
            (POSTER_WIDTH, POSTER_HEIGHT), Image.Resampling.LANCZOS
        )
        # Apply blur for cinematic effect
        backdrop_resized = backdrop_resized.filter(ImageFilter.GaussianBlur(radius=3))
        canvas.paste(backdrop_resized, (0, 0))
        # Dark gradient overlay
        overlay = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        for y in range(POSTER_HEIGHT):
            alpha = int(180 + (60 * y / POSTER_HEIGHT))
            alpha = min(alpha, 240)
            overlay_draw.line([(0, y), (POSTER_WIDTH, y)], fill=(0, 0, 0, alpha))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(canvas)

    # Draw "NOW PLAYING" badge
    badge_text = "NOW PLAYING"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_width = badge_bbox[2] - badge_bbox[0] + 50
    draw.rounded_rectangle(
        [POSTER_LEFT_MARGIN, BADGE_TOP, POSTER_LEFT_MARGIN + badge_width, BADGE_TOP + BADGE_HEIGHT],
        radius=10,
        fill=(229, 9, 20),  # Netflix red
    )
    draw.text(
        (POSTER_LEFT_MARGIN + 25, BADGE_TOP + 11),
        badge_text,
        fill="white",
        font=font_badge,
    )

    # Draw poster image
    if poster:
        poster_height = int(POSTER_DISPLAY_WIDTH * poster.height / poster.width)
        poster_resized = poster.resize(
            (POSTER_DISPLAY_WIDTH, poster_height), Image.Resampling.LANCZOS
        )
        # Add subtle shadow
        canvas.paste(poster_resized, (POSTER_LEFT_MARGIN, POSTER_TOP_MARGIN))

    # Draw title — text column starts after poster + generous gap
    text_x = POSTER_LEFT_MARGIN + POSTER_DISPLAY_WIDTH + 70
    text_y = POSTER_TOP_MARGIN
    text_max_width = POSTER_WIDTH - text_x - 60

    # Word-wrap title if too long
    _draw_wrapped_text(
        draw, title, font_title, text_x, text_y,
        max_width=text_max_width,
        fill="white",
        line_spacing=14,
    )

    # Calculate how many lines the title took
    title_lines = _count_wrapped_lines(
        draw, title, font_title, text_max_width
    )
    title_bbox = draw.textbbox((0, 0), "Ay", font=font_title)
    title_line_height = title_bbox[3] - title_bbox[1] + 14
    meta_y = text_y + title_lines * title_line_height + 28

    # Draw year and rating
    meta_parts = []
    if year:
        meta_parts.append(year)
    if rating is not None:
        meta_parts.append(f"\u2605 {rating:.1f}/10")
    if meta_parts:
        draw.text(
            (text_x, meta_y),
            "  \u2022  ".join(meta_parts),
            fill=(210, 210, 210),
            font=font_meta,
        )
        meta_y += 60

    # Draw genres
    if genres:
        draw.text(
            (text_x, meta_y),
            genres,
            fill=(180, 180, 180),
            font=font_meta,
        )
        meta_y += 64

    # Draw overview (truncated) — fewer chars since font is bigger
    if overview:
        truncated = overview[:220] + ("..." if len(overview) > 220 else "")
        _draw_wrapped_text(
            draw, truncated, font_overview, text_x, meta_y,
            max_width=text_max_width,
            fill=(160, 160, 160),
            line_spacing=10,
            max_lines=5,
        )

    # Encode to PNG
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    x: int,
    y: int,
    max_width: int,
    fill: str | tuple = "white",
    line_spacing: int = 5,
    max_lines: int = 0,
) -> int:
    """Draw word-wrapped text. Returns the number of lines drawn."""
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    if max_lines > 0:
        lines = lines[:max_lines]

    bbox = draw.textbbox((0, 0), "Ay", font=font)
    line_height = bbox[3] - bbox[1] + line_spacing

    for i, line in enumerate(lines):
        draw.text((x, y + i * line_height), line, fill=fill, font=font)

    return len(lines)


def _count_wrapped_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> int:
    """Count how many lines text would wrap to."""
    words = text.split()
    lines = 1
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] > max_width:
            lines += 1
            current_line = word
        else:
            current_line = test_line

    return lines


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

    Downloads images from TMDB and composites them into a styled display.
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
        title,
        year,
        rating,
        genres,
        overview,
    )


async def generate_idle_image(hass: HomeAssistant) -> bytes:
    """Generate a default idle state image."""
    return await hass.async_add_executor_job(_generate_idle_image_sync)


def _generate_idle_image_sync() -> bytes:
    """Generate a simple idle state image (CPU-bound)."""
    canvas = Image.new("RGB", (POSTER_WIDTH, POSTER_HEIGHT), (15, 15, 15))
    draw = ImageDraw.Draw(canvas)

    font_title = _load_default_font(72)
    font_sub = _load_default_font(36)

    # Center text
    title = "Movie Night"
    subtitle = "Select a movie or show to get started"

    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(
        ((POSTER_WIDTH - title_w) // 2, POSTER_HEIGHT // 2 - 70),
        title,
        fill="white",
        font=font_title,
    )

    sub_bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
    sub_w = sub_bbox[2] - sub_bbox[0]
    draw.text(
        ((POSTER_WIDTH - sub_w) // 2, POSTER_HEIGHT // 2 + 30),
        subtitle,
        fill=(130, 130, 130),
        font=font_sub,
    )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
