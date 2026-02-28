"""Constants for the Movie Night integration."""

DOMAIN = "movie_night"

# TMDB API
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
NETFLIX_PROVIDER_ID = 8

# Config keys
CONF_API_KEY = "api_key"
CONF_COUNTRY = "country"
CONF_APPLE_TV_ENTITY = "apple_tv_entity"
CONF_POLL_INTERVAL = "poll_interval"

# Defaults
DEFAULT_COUNTRY = "GB"
DEFAULT_POLL_INTERVAL = 6  # hours
DEFAULT_CATALOG_PAGES = 3  # pages per content type

# Image sizes
POSTER_SIZE_THUMB = "w185"
POSTER_SIZE_MEDIUM = "w500"
POSTER_SIZE_LARGE = "w780"
BACKDROP_SIZE_LARGE = "w1280"
BACKDROP_SIZE_ORIGINAL = "original"

# Poster generator
POSTER_WIDTH = 1920
POSTER_HEIGHT = 1080

# Browse media content ID prefixes
BROWSE_ROOT = "netflix"
BROWSE_MOVIES = "netflix/movies"
BROWSE_TV = "netflix/tv"
BROWSE_MOVIES_POPULAR = "netflix/movies/popular"
BROWSE_TV_POPULAR = "netflix/tv/popular"
BROWSE_MOVIES_GENRE = "netflix/movies/genre"
BROWSE_TV_GENRE = "netflix/tv/genre"

# Frontend
URL_BASE = "/movie-night"

# Events
EVENT_PLAYBACK_STARTED = f"{DOMAIN}_playback_started"


# Platforms
PLATFORMS = ["media_player", "sensor", "camera"]
