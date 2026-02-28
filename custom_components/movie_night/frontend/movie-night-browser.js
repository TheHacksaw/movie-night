/**
 * Movie Night - Browser Card
 *
 * A custom Lovelace card for browsing the Netflix catalog,
 * searching titles, and selecting movies/shows.
 *
 * Config:
 *   type: custom:movie-night-browser
 *   entity: media_player.movie_night_player  (optional, auto-detected)
 */

class MovieNightBrowserCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._results = [];
    this._searching = false;
    this._searchQuery = "";
    this._selectedDetail = null;
    this._activeTab = "movies"; // "movies" or "tv"
    this._loading = false;
  }

  setConfig(config) {
    this._config = config;
    this._renderShell();
  }

  set hass(hass) {
    this._hass = hass;
    // Update the now-playing indicator if visible
    this._updateNowPlaying();
  }

  _findEntityId() {
    if (this._config.entity) return this._config.entity;
    if (!this._hass) return null;
    for (const id of Object.keys(this._hass.states)) {
      if (id.startsWith("media_player.movie_night")) return id;
    }
    return null;
  }

  _renderShell() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          background: #141414;
          color: #fff;
          border-radius: var(--ha-card-border-radius, 12px);
          overflow: hidden;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px 20px;
          background: #1a1a1a;
          border-bottom: 1px solid #2a2a2a;
          flex-wrap: wrap;
        }
        .header-title {
          font-size: 18px;
          font-weight: 700;
          color: #e50914;
          margin-right: auto;
        }
        .search-box {
          display: flex;
          align-items: center;
          background: #333;
          border-radius: 6px;
          overflow: hidden;
          flex: 1;
          min-width: 200px;
          max-width: 400px;
        }
        .search-box input {
          flex: 1;
          background: none;
          border: none;
          color: #fff;
          padding: 8px 12px;
          font-size: 14px;
          outline: none;
        }
        .search-box input::placeholder {
          color: #888;
        }
        .search-btn {
          background: #e50914;
          border: none;
          color: #fff;
          padding: 8px 14px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 600;
        }
        .search-btn:hover { background: #f40612; }
        .tabs {
          display: flex;
          gap: 0;
          background: #1a1a1a;
          border-bottom: 1px solid #2a2a2a;
        }
        .tab {
          flex: 1;
          text-align: center;
          padding: 10px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          color: #888;
          border-bottom: 2px solid transparent;
          transition: all 0.2s;
        }
        .tab:hover { color: #ccc; }
        .tab.active {
          color: #fff;
          border-bottom-color: #e50914;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
          gap: 16px;
          padding: 20px;
          min-height: 200px;
        }
        .poster-card {
          cursor: pointer;
          border-radius: 6px;
          overflow: hidden;
          transition: transform 0.2s, box-shadow 0.2s;
          background: #222;
          position: relative;
        }
        .poster-card:hover {
          transform: scale(1.05);
          box-shadow: 0 8px 24px rgba(0,0,0,0.5);
          z-index: 1;
        }
        .poster-card img {
          width: 100%;
          aspect-ratio: 2/3;
          object-fit: cover;
          display: block;
        }
        .poster-card .no-img {
          width: 100%;
          aspect-ratio: 2/3;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 36px;
          background: #333;
          color: #555;
        }
        .poster-card .card-title {
          padding: 8px;
          font-size: 12px;
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .loading, .empty {
          text-align: center;
          padding: 60px 20px;
          color: #666;
          font-size: 14px;
        }
        .loading::after {
          content: "";
          display: inline-block;
          width: 20px;
          height: 20px;
          border: 2px solid #444;
          border-top-color: #e50914;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
          margin-left: 10px;
          vertical-align: middle;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Detail modal */
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.85);
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .modal {
          background: #1a1a1a;
          border-radius: 12px;
          max-width: 600px;
          width: 100%;
          max-height: 80vh;
          overflow-y: auto;
          box-shadow: 0 16px 48px rgba(0,0,0,0.6);
        }
        .modal-backdrop {
          width: 100%;
          height: 200px;
          object-fit: cover;
          border-radius: 12px 12px 0 0;
        }
        .modal-body {
          padding: 20px;
        }
        .modal-title {
          font-size: 24px;
          font-weight: 700;
          margin-bottom: 8px;
        }
        .modal-meta {
          display: flex;
          gap: 12px;
          font-size: 14px;
          color: #aaa;
          margin-bottom: 8px;
          flex-wrap: wrap;
        }
        .modal-meta .star { color: #f5c518; }
        .modal-genres {
          font-size: 13px;
          color: #777;
          margin-bottom: 12px;
        }
        .modal-overview {
          font-size: 14px;
          color: #bbb;
          line-height: 1.6;
          margin-bottom: 20px;
        }
        .modal-actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        .btn {
          border: none;
          border-radius: 6px;
          padding: 10px 20px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s;
        }
        .btn-primary {
          background: #e50914;
          color: #fff;
        }
        .btn-primary:hover { background: #f40612; }
        .btn-secondary {
          background: #333;
          color: #fff;
        }
        .btn-secondary:hover { background: #444; }
        .btn-close {
          background: #555;
          color: #fff;
        }
        .btn-close:hover { background: #666; }
        .now-playing-badge {
          display: inline-block;
          background: #e50914;
          color: #fff;
          font-size: 11px;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 3px;
          margin-left: 8px;
          vertical-align: middle;
        }

        @media (max-width: 500px) {
          .grid {
            grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
            gap: 10px;
            padding: 12px;
          }
        }
      </style>
      <div class="header">
        <span class="header-title">Movie Night</span>
        ${this._config.show_search !== false ? `
        <div class="search-box">
          <input type="text" id="searchInput" placeholder="Search movies & shows..." />
          <button class="search-btn" id="searchBtn">Search</button>
        </div>` : ""}
      </div>
      ${this._config.show_tabs !== false ? `
      <div class="tabs">
        <div class="tab active" data-tab="movies">Movies</div>
        <div class="tab" data-tab="tv">TV Shows</div>
        <div class="tab" data-tab="search">Search Results</div>
      </div>` : ""}
      <div id="content">
        <div class="loading">Loading catalog</div>
      </div>
      <div id="modalRoot"></div>
    `;

    // Event listeners
    const searchInput = this.shadowRoot.getElementById("searchInput");
    const searchBtn = this.shadowRoot.getElementById("searchBtn");

    if (searchBtn) {
      searchBtn.addEventListener("click", () => this._doSearch());
    }
    if (searchInput) {
      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") this._doSearch();
      });
    }

    this.shadowRoot.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        this._activeTab = tab.dataset.tab;
        this.shadowRoot.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        this._renderContent();
      });
    });

    // Initial load
    this._loadCatalog();
  }

  async _loadCatalog() {
    if (!this._hass) {
      // Retry in a moment when hass is set
      setTimeout(() => this._loadCatalog(), 500);
      return;
    }

    this._loading = true;
    this._renderContent();

    const entityId = this._findEntityId();
    if (!entityId) {
      this._loading = false;
      this._renderContent();
      return;
    }

    try {
      // Use browse_media to get catalog
      const rootMedia = await this._hass.callWS({
        type: "media_player/browse_media",
        entity_id: entityId,
      });

      this._catalogRoot = rootMedia;
      this._loading = false;
      this._renderContent();
    } catch (err) {
      console.warn("Movie Night: Failed to load catalog via browse_media", err);
      this._loading = false;
      this._renderContent();
    }
  }

  async _browseTo(contentId) {
    const entityId = this._findEntityId();
    if (!entityId || !this._hass) return null;

    try {
      return await this._hass.callWS({
        type: "media_player/browse_media",
        entity_id: entityId,
        media_content_type: "app",
        media_content_id: contentId,
      });
    } catch (err) {
      console.warn("Movie Night: browse_media failed for", contentId, err);
      return null;
    }
  }

  async _doSearch() {
    const input = this.shadowRoot.getElementById("searchInput");
    const query = (input ? input.value : "").trim();
    if (!query || !this._hass) return;

    this._searchQuery = query;
    this._activeTab = "search";
    this.shadowRoot.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    this.shadowRoot.querySelector('.tab[data-tab="search"]').classList.add("active");

    this._loading = true;
    this._renderContent();

    try {
      const result = await this._hass.callService("movie_night", "search", { query }, {}, false, true);
      this._results = (result && result.response && result.response.results) || [];
    } catch (err) {
      console.warn("Movie Night: search failed", err);
      this._results = [];
    }

    this._loading = false;
    this._renderContent();
  }

  async _renderContent() {
    const content = this.shadowRoot.getElementById("content");
    if (!content) return;

    if (this._loading) {
      content.innerHTML = '<div class="loading">Loading</div>';
      return;
    }

    if (this._activeTab === "search") {
      this._renderSearchResults(content);
      return;
    }

    // Browse catalog
    const contentId =
      this._activeTab === "movies" ? "netflix/movies/popular" : "netflix/tv/popular";

    const browseData = await this._browseTo(contentId);
    if (!browseData || !browseData.children || browseData.children.length === 0) {
      content.innerHTML = '<div class="empty">No titles found. Check your TMDB configuration.</div>';
      return;
    }

    this._renderGrid(content, browseData.children);
  }

  _renderSearchResults(content) {
    if (this._results.length === 0) {
      content.innerHTML = `<div class="empty">
        ${this._searchQuery ? "No results found for &quot;" + this._escapeHtml(this._searchQuery) + "&quot;" : "Use the search bar above to find movies and shows."}
      </div>`;
      return;
    }

    this._renderSearchGrid(content, this._results);
  }

  _renderGrid(container, items) {
    let html = '<div class="grid">';
    for (const item of items) {
      const title = item.title || "Untitled";
      const thumb = item.thumbnail || "";
      html += `
        <div class="poster-card" data-id="${this._escapeAttr(item.media_content_id)}" data-type="${this._escapeAttr(item.media_content_type || "app")}">
          ${thumb ? `<img src="${this._escapeAttr(thumb)}" alt="${this._escapeAttr(title)}" loading="lazy" />` : `<div class="no-img">&#127910;</div>`}
          <div class="card-title">${this._escapeHtml(title)}</div>
        </div>
      `;
    }
    html += "</div>";
    container.innerHTML = html;

    // Attach click handlers
    container.querySelectorAll(".poster-card").forEach((card) => {
      card.addEventListener("click", () => {
        const mediaId = card.dataset.id;
        const mediaType = card.dataset.type;
        this._onCardClick(mediaId, mediaType);
      });
    });
  }

  _renderSearchGrid(container, items) {
    let html = '<div class="grid">';
    for (const item of items) {
      const title = item.title || "Untitled";
      const thumb = item.poster_url || "";
      html += `
        <div class="poster-card" data-tmdb-id="${item.tmdb_id}" data-content-type="${this._escapeAttr(item.content_type || "movie")}">
          ${thumb ? `<img src="${this._escapeAttr(thumb)}" alt="${this._escapeAttr(title)}" loading="lazy" />` : `<div class="no-img">&#127910;</div>`}
          <div class="card-title">${this._escapeHtml(title)}</div>
        </div>
      `;
    }
    html += "</div>";
    container.innerHTML = html;

    container.querySelectorAll(".poster-card").forEach((card) => {
      card.addEventListener("click", () => {
        const tmdbId = card.dataset.tmdbId;
        const contentType = card.dataset.contentType;
        const item = items.find((i) => String(i.tmdb_id) === tmdbId);
        if (item) this._showSearchDetail(item);
      });
    });
  }

  async _onCardClick(mediaId, mediaType) {
    if (!this._hass) return;
    const entityId = this._findEntityId();
    if (!entityId) return;

    // Play the media (which selects it)
    try {
      await this._hass.callService("media_player", "play_media", {
        entity_id: entityId,
        media_content_type: mediaType,
        media_content_id: mediaId,
      });
    } catch (err) {
      console.warn("Movie Night: play_media failed", err);
    }
  }

  _showSearchDetail(item) {
    this._selectedDetail = item;
    const modalRoot = this.shadowRoot.getElementById("modalRoot");
    if (!modalRoot) return;

    const year = item.year || "";
    const rating = item.rating != null ? item.rating.toFixed(1) : "";
    const overview = item.overview || "";
    const posterUrl = item.poster_url || "";
    const contentType = item.content_type || "movie";
    const typeLabel = contentType === "tv" ? "TV Show" : "Movie";

    modalRoot.innerHTML = `
      <div class="modal-overlay" id="modalOverlay">
        <div class="modal">
          ${posterUrl ? `<img class="modal-backdrop" src="${this._escapeAttr(posterUrl)}" alt="" />` : ""}
          <div class="modal-body">
            <div class="modal-title">${this._escapeHtml(item.title)}</div>
            <div class="modal-meta">
              <span>${typeLabel}</span>
              ${year ? `<span>${year}</span>` : ""}
              ${rating ? `<span class="star">&#9733; ${rating}/10</span>` : ""}
            </div>
            ${overview ? `<div class="modal-overview">${this._escapeHtml(overview)}</div>` : ""}
            <div class="modal-actions">
              <button class="btn btn-primary" id="selectBtn">Select Title</button>
              <button class="btn btn-secondary" id="playBtn">Start Playback</button>
              <button class="btn btn-close" id="closeBtn">Close</button>
            </div>
          </div>
        </div>
      </div>
    `;

    modalRoot.querySelector("#closeBtn").addEventListener("click", () => {
      modalRoot.innerHTML = "";
      this._selectedDetail = null;
    });
    modalRoot.querySelector("#modalOverlay").addEventListener("click", (e) => {
      if (e.target.id === "modalOverlay") {
        modalRoot.innerHTML = "";
        this._selectedDetail = null;
      }
    });
    modalRoot.querySelector("#selectBtn").addEventListener("click", () => {
      this._selectTitle(item.tmdb_id, item.content_type);
      modalRoot.innerHTML = "";
      this._selectedDetail = null;
    });
    modalRoot.querySelector("#playBtn").addEventListener("click", () => {
      this._selectAndPlay(item.tmdb_id, item.content_type);
      modalRoot.innerHTML = "";
      this._selectedDetail = null;
    });
  }

  async _selectTitle(tmdbId, contentType) {
    if (!this._hass) return;
    try {
      await this._hass.callService("movie_night", "select_title", {
        tmdb_id: String(tmdbId),
        content_type: contentType || "movie",
      });
    } catch (err) {
      console.warn("Movie Night: select_title failed", err);
    }
  }

  async _selectAndPlay(tmdbId, contentType) {
    if (!this._hass) return;
    await this._selectTitle(tmdbId, contentType);
    try {
      await this._hass.callService("movie_night", "start_playback", {});
    } catch (err) {
      console.warn("Movie Night: start_playback failed", err);
    }
  }

  _updateNowPlaying() {
    // Could update a "now playing" badge on the currently selected card
    // For now this is a no-op; the poster card handles display
  }

  _escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  _escapeAttr(str) {
    return (str || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  getCardSize() {
    return 8;
  }

  static getConfigElement() {
    return document.createElement("movie-night-browser-editor");
  }

  static getStubConfig() {
    return { entity: "" };
  }
}

customElements.define("movie-night-browser", MovieNightBrowserCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "movie-night-browser",
  name: "Movie Night - Browser",
  description: "Browse and search Netflix catalog with a poster grid.",
  preview: true,
});


/* ───────────────────────────────────────────────
 *  Visual Config Editor
 * ─────────────────────────────────────────────── */
class MovieNightBrowserEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const picker = this.shadowRoot && this.shadowRoot.querySelector("ha-entity-picker");
    if (picker) picker.hass = hass;
  }

  _render() {
    if (!this.shadowRoot) return;

    const showSearch = this._config.show_search !== false;
    const showTabs = this._config.show_tabs !== false;

    this.shadowRoot.innerHTML = `
      <style>
        .editor {
          display: flex;
          flex-direction: column;
          gap: 16px;
          padding: 16px 0;
        }
        .row {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .row label {
          font-size: 14px;
          font-weight: 500;
        }
        .row .secondary {
          font-size: 12px;
          color: var(--secondary-text-color, #888);
        }
        ha-entity-picker {
          display: block;
          width: 100%;
        }
        ha-switch {
          --mdc-theme-secondary: var(--primary-color);
        }
      </style>
      <div class="editor">

        <ha-entity-picker
          .hass=${this._hass}
          .value="${this._config.entity || ""}"
          .includeDomains=${["media_player"]}
          label="Entity (auto-detected if empty)"
          allow-custom-entity
        ></ha-entity-picker>

        <div class="row">
          <div>
            <label>Show search bar</label><br/>
            <span class="secondary">Display the search input</span>
          </div>
          <ha-switch id="showSearch" ${showSearch ? "checked" : ""}></ha-switch>
        </div>

        <div class="row">
          <div>
            <label>Show tabs</label><br/>
            <span class="secondary">Show Movies / TV Shows / Search tabs</span>
          </div>
          <ha-switch id="showTabs" ${showTabs ? "checked" : ""}></ha-switch>
        </div>

      </div>
    `;

    // Wire up entity picker
    const picker = this.shadowRoot.querySelector("ha-entity-picker");
    if (picker) {
      picker.hass = this._hass;
      picker.addEventListener("value-changed", (e) => {
        this._updateConfig("entity", e.detail.value || "");
      });
    }

    // Wire up toggles
    this._wireSwitch("showSearch", "show_search");
    this._wireSwitch("showTabs", "show_tabs");
  }

  _wireSwitch(elementId, configKey) {
    const sw = this.shadowRoot.getElementById(elementId);
    if (sw) {
      sw.addEventListener("change", (e) => {
        this._updateConfig(configKey, e.target.checked);
      });
    }
  }

  _updateConfig(key, value) {
    this._config = { ...this._config, [key]: value };
    const event = new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

customElements.define("movie-night-browser-editor", MovieNightBrowserEditor);
