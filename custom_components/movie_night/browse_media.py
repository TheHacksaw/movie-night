"""Browse media helpers for the Movie Night integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaType,
)

from .const import (
    BROWSE_MOVIES,
    BROWSE_MOVIES_GENRE,
    BROWSE_MOVIES_POPULAR,
    BROWSE_ROOT,
    BROWSE_TV,
    BROWSE_TV_GENRE,
    BROWSE_TV_POPULAR,
)
from .coordinator import MovieNightCoordinator
from .tmdb_client import TMDBClient


async def async_browse_media(
    coordinator: MovieNightCoordinator,
    media_content_type: str | None,
    media_content_id: str | None,
) -> BrowseMedia:
    """Build a BrowseMedia tree for the Netflix catalog."""
    if media_content_id is None or media_content_id == BROWSE_ROOT:
        return _build_root()

    if media_content_id == BROWSE_MOVIES:
        return _build_content_type_menu("Movies", BROWSE_MOVIES, coordinator, "movie")

    if media_content_id == BROWSE_TV:
        return _build_content_type_menu("TV Shows", BROWSE_TV, coordinator, "tv")

    if media_content_id == BROWSE_MOVIES_POPULAR:
        return _build_title_list(
            "Popular Movies",
            BROWSE_MOVIES_POPULAR,
            coordinator.data.get("movies", []),
            "movie",
        )

    if media_content_id == BROWSE_TV_POPULAR:
        return _build_title_list(
            "Popular TV Shows",
            BROWSE_TV_POPULAR,
            coordinator.data.get("tv", []),
            "tv",
        )

    if media_content_id.startswith(BROWSE_MOVIES_GENRE + "/"):
        genre_id = int(media_content_id.split("/")[-1])
        genre_name = coordinator.genres.get("movie", {}).get(genre_id, "Unknown")
        movies = [
            m
            for m in coordinator.data.get("movies", [])
            if genre_id in m.get("genre_ids", [])
        ]
        return _build_title_list(
            f"Movies: {genre_name}",
            media_content_id,
            movies,
            "movie",
        )

    if media_content_id.startswith(BROWSE_TV_GENRE + "/"):
        genre_id = int(media_content_id.split("/")[-1])
        genre_name = coordinator.genres.get("tv", {}).get(genre_id, "Unknown")
        shows = [
            s
            for s in coordinator.data.get("tv", [])
            if genre_id in s.get("genre_ids", [])
        ]
        return _build_title_list(
            f"TV Shows: {genre_name}",
            media_content_id,
            shows,
            "tv",
        )

    # Shouldn't reach here, return root
    return _build_root()


def _build_root() -> BrowseMedia:
    """Build the root browse node."""
    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=BROWSE_ROOT,
        media_content_type=MediaType.VIDEO,
        title="Netflix Catalog",
        can_play=False,
        can_expand=True,
        children=[
            BrowseMedia(
                media_class=MediaClass.DIRECTORY,
                media_content_id=BROWSE_MOVIES,
                media_content_type=MediaType.MOVIE,
                title="Movies",
                can_play=False,
                can_expand=True,
                children_media_class=MediaClass.DIRECTORY,
            ),
            BrowseMedia(
                media_class=MediaClass.DIRECTORY,
                media_content_id=BROWSE_TV,
                media_content_type=MediaType.TVSHOW,
                title="TV Shows",
                can_play=False,
                can_expand=True,
                children_media_class=MediaClass.DIRECTORY,
            ),
        ],
    )


def _build_content_type_menu(
    title: str,
    content_id: str,
    coordinator: MovieNightCoordinator,
    content_type: str,
) -> BrowseMedia:
    """Build a menu for a content type (Movies or TV Shows) with Popular + genres."""
    genre_prefix = (
        BROWSE_MOVIES_GENRE if content_type == "movie" else BROWSE_TV_GENRE
    )
    popular_id = (
        BROWSE_MOVIES_POPULAR if content_type == "movie" else BROWSE_TV_POPULAR
    )

    children = [
        BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=popular_id,
            media_content_type=MediaType.VIDEO,
            title="Popular",
            can_play=False,
            can_expand=True,
        ),
    ]

    # Add genre directories
    genres = coordinator.genres.get(content_type, {})
    catalog = coordinator.data.get(
        "movies" if content_type == "movie" else "tv", []
    )

    # Only show genres that have content in the catalog
    genre_ids_with_content = set()
    for item in catalog:
        for gid in item.get("genre_ids", []):
            genre_ids_with_content.add(gid)

    for genre_id, genre_name in sorted(genres.items(), key=lambda x: x[1]):
        if genre_id in genre_ids_with_content:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=f"{genre_prefix}/{genre_id}",
                    media_content_type=MediaType.VIDEO,
                    title=genre_name,
                    can_play=False,
                    can_expand=True,
                )
            )

    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=content_id,
        media_content_type=MediaType.VIDEO,
        title=title,
        can_play=False,
        can_expand=True,
        children=children,
    )


def _build_title_list(
    title: str,
    content_id: str,
    items: list[dict[str, Any]],
    content_type: str,
) -> BrowseMedia:
    """Build a list of individual movie/show items."""
    media_class = MediaClass.MOVIE if content_type == "movie" else MediaClass.TV_SHOW
    media_type = MediaType.MOVIE if content_type == "movie" else MediaType.TVSHOW

    children = []
    for item in items:
        tmdb_id = item.get("id")
        item_title = item.get("title") or item.get("name", "Unknown")
        poster_path = item.get("poster_path")
        year = (
            item.get("release_date", "")[:4]
            or item.get("first_air_date", "")[:4]
        )
        display_title = f"{item_title} ({year})" if year else item_title

        children.append(
            BrowseMedia(
                media_class=media_class,
                media_content_id=f"netflix/{content_type}/{tmdb_id}",
                media_content_type=media_type,
                title=display_title,
                can_play=True,
                can_expand=False,
                thumbnail=TMDBClient.thumb_url(poster_path),
            )
        )

    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=content_id,
        media_content_type=MediaType.VIDEO,
        title=title,
        can_play=False,
        can_expand=True,
        children=children,
        children_media_class=media_class,
    )
