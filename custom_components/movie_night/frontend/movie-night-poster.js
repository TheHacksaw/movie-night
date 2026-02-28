/**
 * Movie Night - Now Playing Poster Card
 *
 * A custom Lovelace card that displays the currently selected
 * movie or show in a cinematic full-screen layout.
 *
 * Config:
 *   type: custom:movie-night-poster
 *   entity: media_player.movie_night_player  (optional, auto-detected)
 */

class MovieNightPosterCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _getEntity() {
    if (!this._hass) return null;
    const entityId =
      this._config.entity || this._findMovieNightEntity();
    if (!entityId) return null;
    return this._hass.states[entityId] || null;
  }

  _findMovieNightEntity() {
    if (!this._hass) return null;
    const states = this._hass.states;
    for (const id of Object.keys(states)) {
      if (id.startsWith("media_player.movie_night")) {
        return id;
      }
    }
    return null;
  }

  _render() {
    if (!this.shadowRoot) return;
    const entity = this._getEntity();

    const isPlaying = entity && entity.state === "playing";
    const attrs = entity ? entity.attributes || {} : {};

    const title = attrs.media_title || "";
    const year = attrs.year || "";
    const rating = attrs.rating;
    const genres = attrs.genres || "";
    const overview = attrs.overview || "";
    const posterUrl = attrs.poster_url || "";
    const backdropUrl = attrs.backdrop_url || "";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: relative;
          overflow: hidden;
          border-radius: var(--ha-card-border-radius, 12px);
          background: #0f0f0f;
          color: #fff;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .container {
          position: relative;
          width: 100%;
          min-height: 400px;
          aspect-ratio: 16 / 9;
          cursor: pointer;
        }
        .container:active {
          opacity: 0.9;
        }
        .stop-hint {
          position: absolute;
          bottom: 16px;
          right: 16px;
          z-index: 2;
          background: rgba(0,0,0,0.6);
          color: #999;
          font-size: 12px;
          padding: 6px 12px;
          border-radius: 6px;
          opacity: 0;
          transition: opacity 0.2s;
        }
        .container:hover .stop-hint {
          opacity: 1;
        }
        .backdrop {
          position: absolute;
          inset: 0;
          background-size: cover;
          background-position: center;
          filter: blur(2px);
        }
        .backdrop::after {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(
            to right,
            rgba(0,0,0,0.85) 0%,
            rgba(0,0,0,0.6) 50%,
            rgba(0,0,0,0.85) 100%
          );
        }
        .content {
          position: relative;
          z-index: 1;
          display: flex;
          align-items: center;
          gap: 32px;
          padding: 32px;
          height: 100%;
          box-sizing: border-box;
        }
        .poster-img {
          flex-shrink: 0;
          width: 220px;
          border-radius: 8px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.6);
          object-fit: cover;
        }
        .info {
          flex: 1;
          min-width: 0;
        }
        .badge {
          display: inline-block;
          background: #e50914;
          color: #fff;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          padding: 4px 14px;
          border-radius: 4px;
          margin-bottom: 12px;
        }
        .title {
          font-size: 32px;
          font-weight: 700;
          line-height: 1.2;
          margin: 0 0 8px 0;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }
        .meta {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 15px;
          color: #ccc;
          margin-bottom: 10px;
          flex-wrap: wrap;
        }
        .meta .dot {
          color: #666;
        }
        .star {
          color: #f5c518;
        }
        .genres {
          font-size: 14px;
          color: #999;
          margin-bottom: 14px;
        }
        .overview {
          font-size: 14px;
          color: #aaa;
          line-height: 1.5;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 4;
          -webkit-box-orient: vertical;
        }
        .idle-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 400px;
          text-align: center;
          padding: 32px;
          box-sizing: border-box;
        }
        .idle-icon {
          font-size: 64px;
          margin-bottom: 16px;
          opacity: 0.4;
        }
        .idle-title {
          font-size: 24px;
          font-weight: 600;
          margin-bottom: 8px;
          opacity: 0.6;
        }
        .idle-sub {
          font-size: 14px;
          color: #666;
        }
        /* Responsive adjustments */
        @media (max-width: 600px) {
          .content {
            flex-direction: column;
            text-align: center;
            padding: 20px;
            gap: 20px;
          }
          .poster-img {
            width: 160px;
          }
          .title {
            font-size: 24px;
          }
          .meta {
            justify-content: center;
          }
        }
      </style>

      ${isPlaying ? this._renderPlaying(title, year, rating, genres, overview, posterUrl, backdropUrl) : this._renderIdle()}
    `;

    // Attach tap-to-stop handler when playing
    if (isPlaying) {
      const container = this.shadowRoot.querySelector(".container");
      if (container) {
        container.addEventListener("click", () => this._stopMovieNight());
      }
    }
  }

  _renderPlaying(title, year, rating, genres, overview, posterUrl, backdropUrl) {
    const ratingStr = rating != null ? rating.toFixed(1) : "";
    const metaParts = [];
    if (year) metaParts.push(`<span>${year}</span>`);
    if (ratingStr) metaParts.push(`<span class="star">&#9733; ${ratingStr}</span>`);
    const metaHtml = metaParts.join('<span class="dot">&bull;</span>');

    return `
      <div class="container">
        ${backdropUrl ? `<div class="backdrop" style="background-image:url('${backdropUrl}')"></div>` : ""}
        <div class="content">
          ${posterUrl ? `<img class="poster-img" src="${posterUrl}" alt="${this._escapeHtml(title)}" />` : ""}
          <div class="info">
            <span class="badge">Now Playing</span>
            <h2 class="title">${this._escapeHtml(title)}</h2>
            ${metaHtml ? `<div class="meta">${metaHtml}</div>` : ""}
            ${genres ? `<div class="genres">${this._escapeHtml(genres)}</div>` : ""}
            ${overview ? `<div class="overview">${this._escapeHtml(overview)}</div>` : ""}
          </div>
        </div>
        <div class="stop-hint">Tap to stop Movie Night</div>
      </div>
    `;
  }

  _renderIdle() {
    return `
      <div class="idle-container">
        <div class="idle-icon">&#127910;</div>
        <div class="idle-title">Movie Night</div>
        <div class="idle-sub">Select a movie or show to get started</div>
      </div>
    `;
  }

  _stopMovieNight() {
    if (!this._hass) return;
    const entityId = this._config.entity || this._findMovieNightEntity();
    if (!entityId) return;
    this._hass.callService("media_player", "turn_off", {
      entity_id: entityId,
    });
  }

  _escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  getCardSize() {
    return 6;
  }

  static getConfigElement() {
    return document.createElement("movie-night-poster-editor");
  }

  static getStubConfig() {
    return { entity: "" };
  }
}

customElements.define("movie-night-poster", MovieNightPosterCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "movie-night-poster",
  name: "Movie Night - Now Playing",
  description: "Displays the currently selected movie or show in a cinematic layout.",
  preview: true,
});
