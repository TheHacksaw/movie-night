"""Async TMDB API client for the Movie Night integration."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import (
    BACKDROP_SIZE_LARGE,
    NETFLIX_PROVIDER_ID,
    POSTER_SIZE_MEDIUM,
    POSTER_SIZE_THUMB,
    TMDB_API_BASE,
    TMDB_IMAGE_BASE,
)

_LOGGER = logging.getLogger(__name__)


class TMDBClient:
    """Async client for the TMDB API."""

    def __init__(self, session: ClientSession, api_key: str) -> None:
        """Initialize the TMDB client."""
        self._session = session
        self._api_key = api_key

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Make a GET request to the TMDB API."""
        url = f"{TMDB_API_BASE}{path}"
        all_params = {"api_key": self._api_key}
        if params:
            all_params.update(params)
        try:
            async with self._session.get(url, params=all_params) as resp:
                resp.raise_for_status()
                return await resp.json()
        except ClientError as err:
            _LOGGER.error("TMDB API request failed: %s %s", url, err)
            raise ConnectionError(f"TMDB API request failed: {err}") from err

    async def validate_key(self) -> bool:
        """Validate the API key by requesting the TMDB configuration."""
        try:
            result = await self._get("/configuration")
            return "images" in result
        except ConnectionError:
            return False

    async def get_netflix_movies(
        self, country: str, page: int = 1
    ) -> dict[str, Any]:
        """Get movies available on Netflix in the given country."""
        return await self._get(
            "/discover/movie",
            {
                "with_watch_providers": NETFLIX_PROVIDER_ID,
                "watch_region": country,
                "sort_by": "popularity.desc",
                "page": page,
            },
        )

    async def get_netflix_tv(
        self, country: str, page: int = 1
    ) -> dict[str, Any]:
        """Get TV shows available on Netflix in the given country."""
        return await self._get(
            "/discover/tv",
            {
                "with_watch_providers": NETFLIX_PROVIDER_ID,
                "watch_region": country,
                "sort_by": "popularity.desc",
                "page": page,
            },
        )

    async def get_movie_details(self, tmdb_id: int) -> dict[str, Any]:
        """Get detailed information about a movie."""
        return await self._get(
            f"/movie/{tmdb_id}",
            {"append_to_response": "watch/providers"},
        )

    async def get_tv_details(self, tmdb_id: int) -> dict[str, Any]:
        """Get detailed information about a TV show."""
        return await self._get(
            f"/tv/{tmdb_id}",
            {"append_to_response": "watch/providers"},
        )

    async def search(self, query: str) -> dict[str, Any]:
        """Search for movies and TV shows."""
        return await self._get(
            "/search/multi",
            {"query": query, "include_adult": "false"},
        )

    async def get_genres(self) -> dict[str, dict[int, str]]:
        """Get genre lists for movies and TV shows.

        Returns a dict with 'movie' and 'tv' keys, each mapping
        genre IDs to genre names.
        """
        movie_genres_raw = await self._get("/genre/movie/list")
        tv_genres_raw = await self._get("/genre/tv/list")

        movie_genres = {
            g["id"]: g["name"] for g in movie_genres_raw.get("genres", [])
        }
        tv_genres = {
            g["id"]: g["name"] for g in tv_genres_raw.get("genres", [])
        }
        return {"movie": movie_genres, "tv": tv_genres}

    @staticmethod
    def poster_url(path: str | None, size: str = POSTER_SIZE_MEDIUM) -> str | None:
        """Build a full poster image URL from a TMDB path."""
        if not path:
            return None
        return f"{TMDB_IMAGE_BASE}/{size}{path}"

    @staticmethod
    def backdrop_url(
        path: str | None, size: str = BACKDROP_SIZE_LARGE
    ) -> str | None:
        """Build a full backdrop image URL from a TMDB path."""
        if not path:
            return None
        return f"{TMDB_IMAGE_BASE}/{size}{path}"

    @staticmethod
    def thumb_url(path: str | None) -> str | None:
        """Build a thumbnail poster URL from a TMDB path."""
        return TMDBClient.poster_url(path, POSTER_SIZE_THUMB)
