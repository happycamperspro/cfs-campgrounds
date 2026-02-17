# Campground Data Pipeline + Scrapers + Frontend - Implementation Plan

## Context

The Campfire Social app needs a public campground discovery catalog populated from:
1. **Public APIs** — Recreation.gov RIDB (~3,500 federal campgrounds) and NPS API (~500 NPS campgrounds)
2. **Web scraping** — Private campground networks: KOA, Hipcamp, Good Sam, Thousand Trails, state park systems

This project has three parts, all within one workspace:
- **`backend/`** — Python data pipeline (API clients + Scrapy scrapers + transforms + Firestore loader)
- **`frontend/`** — React + Vite campground browser (search, filters, map, detail pages, photos)
- **Root** — Firebase config files (firebase.json, firestore.rules, etc.)

The existing Firebase project (`hcp-social-chat-firebase-host`) is already linked via `.firebaserc`.

**Key finding:** The existing app uses `campgrounds_registry` (see `firestore.rules:67`) for operational campground management. The new `campgrounds` collection is a separate public discovery catalog.

---

## Project Structure

```
campfire-campgrounds/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── regions.py
│   ├── sources/                    # Public API clients
│   │   ├── __init__.py
│   │   ├── base_source.py
│   │   ├── recreation_gov.py
│   │   ├── nps_api.py
│   │   └── google_places.py       # Stub for future
│   ├── scrapers/                   # Scrapy project for private campgrounds
│   │   ├── scrapy.cfg
│   │   └── campground_scrapers/
│   │       ├── __init__.py
│   │       ├── settings.py         # Scrapy settings
│   │       ├── items.py            # Scrapy item definitions
│   │       ├── pipelines.py        # Scrapy pipeline → normalizer → Firestore
│   │       ├── middlewares.py      # Custom download middlewares
│   │       └── spiders/
│   │           ├── __init__.py
│   │           ├── koa.py
│   │           ├── hipcamp.py
│   │           ├── good_sam.py
│   │           ├── thousand_trails.py
│   │           └── state_parks.py
│   ├── transforms/
│   │   ├── __init__.py
│   │   ├── normalizer.py
│   │   ├── geocoder.py
│   │   └── deduplicator.py
│   ├── loaders/
│   │   ├── __init__.py
│   │   └── firestore_loader.py
│   ├── scripts/
│   │   ├── run_full_sync.py
│   │   ├── run_incremental_sync.py
│   │   ├── run_single_source.py
│   │   └── run_scraper.py          # Run individual Scrapy spiders
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_recreation_gov.py
│   │   ├── test_normalizer.py
│   │   └── test_firestore_loader.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/                       # React + Vite
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── config/firebase.js
│       ├── hooks/
│       ├── context/
│       ├── lib/
│       ├── components/
│       └── pages/
├── functions/                      # Existing Cloud Functions
│   ├── main.py
│   └── requirements.txt
├── .firebaserc
├── firebase.json
├── firestore.rules
├── firestore.indexes.json
├── .gitignore
└── .idx/dev.nix
```

---

## Part 1: Backend (API Pipeline + Scrapers)

### Phase 1: Foundation (config, dependencies, .env)

**Files to create:**
- `backend/requirements.txt` — dependencies:
  ```
  firebase-admin>=6.0.0
  google-cloud-firestore>=2.11.0
  requests>=2.31.0
  python-dotenv>=1.0.0
  geopy>=2.3.0
  tenacity>=8.2.0
  tqdm>=4.65.0
  Scrapy>=2.11.0
  scrapy-fake-useragent>=1.4.4
  pytest>=7.0.0
  ```
- `backend/.env.example` — template with `RECREATION_GOV_API_KEY`, `NPS_API_KEY`, `GOOGLE_PLACES_API_KEY`, `FIREBASE_PROJECT_ID`
- `backend/.env` — actual keys (gitignored)
- `backend/config/__init__.py`
- `backend/config/settings.py` — loads `.env`, defines API URLs, rate limits, batch sizes, collection name
- `backend/config/regions.py` — `STATE_TO_REGION` mapping using user's exact regions (Northeast, Southeast, Midwest, Southwest, Rocky Mountain, Pacific Northwest, Pacific, Alaska), `STATE_ABBREVIATIONS` dict, `get_region()` and `normalize_state()` helpers

### Phase 2: Source Layer (public API clients)

**Files to create:**
- `backend/sources/__init__.py`
- `backend/sources/base_source.py` — `BaseSource` ABC with:
  - `requests.Session` management
  - `_rate_limit()` — enforces delay between requests
  - `_get()` — rate-limited GET with `tenacity` retry (3 attempts, exponential backoff)
  - `_paginate()` — generic paginator yielding individual records
  - Abstract: `fetch_all_campgrounds()` (generator), `fetch_campground_detail()`, `source_name` property
- `backend/sources/recreation_gov.py` — `RecreationGovSource(BaseSource)`:
  - Auth via `apikey` header, 0.5s rate limit
  - `fetch_all_campgrounds()` — `GET /facilities?activity=CAMPING&full=true`, paginated with `offset`/`limit` (max 50)
  - `fetch_campground_detail()`, `fetch_campsites_for_facility()`, `fetch_media_for_facility()`, `fetch_addresses_for_facility()`
- `backend/sources/nps_api.py` — `NPSSource(BaseSource)`:
  - Auth via `X-Api-Key` header
  - `fetch_all_campgrounds()` — `GET /campgrounds`, paginated with `start`/`limit`
  - Custom pagination (NPS uses `start`/`total` instead of `offset`/`METADATA`)
  - `fetch_campground_detail()`, `fetch_park_info()`
- `backend/sources/google_places.py` — stub with `NotImplementedError` for future enrichment

### Phase 3: Transform Layer (normalize, geocode, deduplicate)

**Files to create:**
- `backend/transforms/__init__.py`
- `backend/transforms/normalizer.py` — the most critical module:
  - `generate_slug(name, state, city)` — URL-safe, lowercase, hyphenated
  - `strip_html(text)` — removes HTML tags, unescapes entities
  - `normalize_recreation_gov(facility, campsites=None)` — maps RIDB JSON → unified schema, sets `_doc_id = "recreation_gov_{FacilityID}"`
  - `normalize_nps(campground)` — maps NPS JSON → unified schema, sets `_doc_id = "nps_{id}"`
  - `normalize_scraped(item, source_name)` — maps Scrapy items → unified schema, sets `_doc_id = "{source}_{source_id}"`
  - All produce dicts matching the Firestore schema (location, contact, details, amenities, photos, ratings, metadata maps)
  - `ratings` initialized to 0 (never overwritten on updates)
- `backend/transforms/geocoder.py`:
  - `distance_miles()` — via `geopy.distance.geodesic`
  - `geocode_address()` — forward geocode via Nominatim for records missing coordinates
  - `is_within_radius()` — proximity check
- `backend/transforms/deduplicator.py`:
  - `find_duplicates(records)` — cross-source only, fuzzy name (>=0.85 SequenceMatcher) + proximity (<=0.5 miles)
  - `resolve_duplicates(records, duplicates, priority)` — merges data, priority order: NPS > Recreation.gov > KOA > Hipcamp > Good Sam > Thousand Trails > state_parks
  - Name normalization strips common suffixes

### Phase 4: Loader Layer (Firestore writes)

**Files to create:**
- `backend/loaders/__init__.py`
- `backend/loaders/firestore_loader.py` — `FirestoreLoader` class:
  - `_init_firebase()` — Firebase Admin SDK init (idempotent, supports service account or ADC)
  - `upsert_batch(records, dry_run=False)` — batch writes of 500, `set(merge=True)`, pre-fetches existing doc IDs, strips `ratings`/`metadata.createdAt` on updates, removes None values, `tqdm` progress, returns stats
  - `get_existing_doc_ids()` — for incremental sync
  - `delete_stale_records(active_ids, dry_run)` — soft-delete via `metadata.isActive = False`

### Phase 5: Scrapy Scrapers (private campgrounds)

**Files to create:**
- `backend/scrapers/scrapy.cfg` — Scrapy project config pointing to `campground_scrapers.settings`
- `backend/scrapers/campground_scrapers/__init__.py`
- `backend/scrapers/campground_scrapers/settings.py` — Scrapy settings:
  - `ROBOTSTXT_OBEY = True`
  - `CONCURRENT_REQUESTS = 4` (conservative)
  - `DOWNLOAD_DELAY = 2` (respectful crawling)
  - `AUTOTHROTTLE_ENABLED = True`
  - `ITEM_PIPELINES` wired to custom pipeline
  - `FAKEUSERAGENT_PROVIDER = 'scrapy_fake_useragent.providers.FakeUserAgentProvider'`
- `backend/scrapers/campground_scrapers/items.py` — `CampgroundItem(scrapy.Item)` with fields matching the unified schema: name, source, source_id, address, city, state, zip, latitude, longitude, phone, email, website, reservation_url, total_sites, site_types, hookups, facilities, activities, season, price_min, price_max, description, photos, managed_by, pets_allowed, accessibility
- `backend/scrapers/campground_scrapers/pipelines.py` — `FirestorePipeline`:
  - `open_spider()` — inits Firebase, creates `FirestoreLoader`
  - `process_item()` — calls `normalize_scraped(item, spider.source_name)`, buffers items, flushes in batches of 500
  - `close_spider()` — flushes remaining buffer, logs stats
- `backend/scrapers/campground_scrapers/middlewares.py` — custom download middleware for retry/error handling

**Spiders (one per source):**

- `backend/scrapers/campground_scrapers/spiders/koa.py` — `KOASpider`:
  - Source: `koa.com/campgrounds/`
  - Crawl strategy: start from campground directory, follow state/campground links
  - Extract: name, address, coordinates (from embedded map data), amenities, photos, pricing, site types
  - ~500 KOA locations in the US
  - `source_name = "koa"`

- `backend/scrapers/campground_scrapers/spiders/hipcamp.py` — `HipcampSpider`:
  - Source: `hipcamp.com`
  - Crawl strategy: browse listings by state/region
  - Extract: name, location, description, amenities, photos, pricing, ratings
  - Note: Hipcamp is a React SPA — may need `scrapy-splash` or fallback to their sitemap/structured data
  - `source_name = "hipcamp"`

- `backend/scrapers/campground_scrapers/spiders/good_sam.py` — `GoodSamSpider`:
  - Source: `goodsam.com/campgrounds-rv-parks/`
  - Crawl strategy: search by state, paginate through results
  - Extract: name, address, amenities, ratings, hookup types, pull-through vs back-in
  - Strong RV park data — hookup details, max RV length, pull-through availability
  - `source_name = "good_sam"`

- `backend/scrapers/campground_scrapers/spiders/thousand_trails.py` — `ThousandTrailsSpider`:
  - Source: `thousandtrails.com/find-a-campground`
  - Crawl strategy: location search, detail page extraction
  - Extract: name, address, amenities, photos, activities
  - ~80 locations
  - `source_name = "thousand_trails"`

- `backend/scrapers/campground_scrapers/spiders/state_parks.py` — `StateParksSpider`:
  - Source: `stateparks.org` and individual state park reservation systems
  - Crawl strategy: start from state directory, follow links to individual campgrounds
  - Extract: name, park name, address, site count, amenities, season, fees
  - Start with high-value states (CA, CO, TX, FL, OR, WA) and expand
  - `source_name = "state_parks"`

### Phase 6: Orchestration Scripts

**Files to create:**
- `backend/scripts/run_single_source.py` — CLI: `python run_single_source.py recreation_gov --limit 10 [--load] [--dry-run]`
- `backend/scripts/run_full_sync.py` — CLI: `python run_full_sync.py [--dry-run]`
  - Phase 1: Fetch + normalize from Recreation.gov
  - Phase 2: Fetch + normalize from NPS
  - Phase 3: Run all Scrapy spiders and collect results
  - Phase 4: Cross-source deduplication across all sources
  - Phase 5: Batch upsert to Firestore
  - Phase 6: Soft-delete stale records
- `backend/scripts/run_incremental_sync.py` — incremental sync with timestamp tracking
- `backend/scripts/run_scraper.py` — CLI: `python run_scraper.py koa [--limit 10] [--dry-run]`
  - Runs a single Scrapy spider by name
  - Supports `--limit` for testing, `--dry-run` to skip Firestore writes
  - Uses `CrawlerProcess` to run spiders programmatically

### Phase 7: Tests

**Files to create:**
- `backend/tests/__init__.py`
- `backend/tests/test_recreation_gov.py` — mocked API tests
- `backend/tests/test_normalizer.py` — slug generation, HTML stripping, RIDB/NPS/scraped normalization, edge cases
- `backend/tests/test_firestore_loader.py` — mocked Firestore tests for batch, merge, ratings protection, dry run

### Phase 8: Cloud Function for Scheduled Sync

**Files to create:**
- `backend/functions/scheduled_sync/main.py` — Cloud Function with `@scheduler_fn.on_schedule` trigger
- `backend/functions/scheduled_sync/requirements.txt`

**Note:** Scraping is too long-running for Cloud Functions. The scheduled function should only run the API sync (RIDB + NPS). Scrapers should be run manually or via Cloud Run Jobs.

### Phase 9: Firebase & Dev Environment Updates

**Files to modify:**
- `firestore.rules` — add `campgrounds` collection (public read, no client write), `campgrounds/{id}/reviews` subcollection, `_pipeline_metadata` (admin SDK only)
- `firestore.indexes.json` — add composite indexes:
  1. `metadata.isActive` + `name` — base browse
  2. `metadata.isActive` + `location.state` + `name` — browse by state
  3. `metadata.isActive` + `location.region` + `name` — browse by region
  4. `metadata.isActive` + `details.siteTypes` (ARRAY_CONTAINS) + `name` — filter by site type
  5. `metadata.isActive` + `amenities.hookups` (ARRAY_CONTAINS) + `name` — filter by hookups
  6. `metadata.isActive` + `metadata.updatedAt` (DESC) — admin stale data query
- `.gitignore` — add `__pycache__/`, `*.pyc`, `venv/`, `service-account.json`, `frontend/dist/`, `backend/.env`
- `firebase.json` — add `hosting` section pointing to `frontend/dist` with SPA rewrite
- `.idx/dev.nix` — uncomment `pkgs.nodejs_20`, add Vite web preview config

### Phase 10: Backend Documentation

- `backend/README.md` — setup, run order, spider descriptions, architecture

---

## Part 2: React + Vite Frontend

### Phase 11: Frontend Scaffold

- Scaffold Vite + React in `frontend/`
- Dependencies: `react`, `react-dom`, `react-router-dom`, `firebase`, `leaflet`, `react-leaflet`, `react-leaflet-markercluster`, `yet-another-react-lightbox`
- Dev deps: `@vitejs/plugin-react`, `vite`, `tailwindcss`, `postcss`, `autoprefixer`
- Configure Tailwind, PostCSS, Vite (manual chunks for firebase/leaflet, host 0.0.0.0)

### Phase 12: Firebase Config + Core Hooks

**Files to create:**
- `frontend/src/config/firebase.js` — Firebase app init, Firestore with persistent local cache
- `frontend/src/lib/queries.js` — Firestore query builders: browse (paginated), by state, by region, filtered (compound), by slug, search (prefix range)
- `frontend/src/lib/constants.js` — US states, regions, amenity options, site types
- `frontend/src/lib/utils.js` — formatting helpers
- `frontend/src/hooks/useFirestore.js` — generic query hook → `{ data, loading, error, lastDoc }`
- `frontend/src/hooks/useCampgrounds.js` — filter-aware campground fetching with client-side post-filtering
- `frontend/src/hooks/useCampground.js` — single campground by slug
- `frontend/src/hooks/useSearch.js` — debounced search (300ms)
- `frontend/src/hooks/usePagination.js` — cursor-based pagination
- `frontend/src/context/FilterContext.jsx` — useReducer filter state (state, region, siteTypes[], hookups[], facilities[], petsAllowed, accessible, managedBy, sortBy)

### Phase 13: Layout + Routing

**Files to create:**
- `frontend/src/App.jsx` — routes: `/` Home, `/browse` Browse, `/browse/:state` State, `/campground/:slug` Detail, `/map` Map, `*` 404
- `frontend/src/components/layout/Layout.jsx` — Header + Outlet + Footer, wraps in FilterProvider
- `frontend/src/components/layout/Header.jsx` — nav, logo, Browse/Map links, SearchBar, mobile hamburger
- `frontend/src/components/layout/Footer.jsx` — attribution, region links

### Phase 14: Browse Experience (Cards + Grid + Filters)

**Files to create:**
- `frontend/src/pages/HomePage.jsx` — hero, featured campgrounds, browse-by-state/region
- `frontend/src/pages/BrowsePage.jsx` — filters sidebar + grid + map toggle
- `frontend/src/pages/StatePage.jsx` — campgrounds in a state, pre-filtered
- `frontend/src/components/campground/CampgroundCard.jsx` — lazy photo, name, location, rating, price, source badge
- `frontend/src/components/campground/CampgroundGrid.jsx` — responsive grid (1/2/3 cols), LoadMore, loading/empty states
- `frontend/src/components/campground/RatingStars.jsx`, `PriceRange.jsx`
- `frontend/src/components/filters/FilterPanel.jsx` — sidebar (desktop) / drawer (mobile)
- `frontend/src/components/filters/StateFilter.jsx`, `RegionFilter.jsx`, `AmenityFilter.jsx`, `SiteTypeFilter.jsx`, `ActiveFilters.jsx`
- `frontend/src/components/ui/LoadingSpinner.jsx`, `ErrorMessage.jsx`, `EmptyState.jsx`, `Pagination.jsx`

### Phase 15: Campground Detail Page

**Files to create:**
- `frontend/src/pages/CampgroundPage.jsx` — fetch by slug, render detail
- `frontend/src/components/campground/CampgroundDetail.jsx` — hero photo, description, amenities, contact, site details, mini map, reservation button
- `frontend/src/components/campground/AmenityBadge.jsx`, `AmenityList.jsx`, `ContactInfo.jsx`
- `frontend/src/components/gallery/PhotoGallery.jsx` — thumbnail grid, opens lightbox
- `frontend/src/components/gallery/Lightbox.jsx` — full-screen via `yet-another-react-lightbox`
- `frontend/src/components/map/DetailMap.jsx` — small Leaflet map centered on campground

### Phase 16: Interactive Map Page

**Files to create:**
- `frontend/src/pages/MapPage.jsx` — full-screen map (lazy-loaded)
- `frontend/src/components/map/CampgroundMap.jsx` — Leaflet + OpenStreetMap, marker clustering
- `frontend/src/components/map/MapMarker.jsx` — custom marker with popup

### Phase 17: Search

**Files to create:**
- `frontend/src/components/search/SearchBar.jsx` — debounced input, Escape to clear
- `frontend/src/components/search/SearchResults.jsx` — dropdown, up to 8 matches

### Phase 18: Admin Dashboard (super_admin only)

**Auth integration:**
- `frontend/src/hooks/useAuth.js` — auth state hook, returns `{ user, loading, isSuperAdmin }`
- `frontend/src/context/AuthContext.jsx` — provides auth state globally
- `frontend/src/components/admin/AdminRoute.jsx` — route guard: checks `isSuperAdmin`, redirects to login

**Admin pages:**
- `frontend/src/pages/admin/AdminLoginPage.jsx` — Firebase Auth sign-in
- `frontend/src/pages/admin/DashboardPage.jsx` — overview: total campgrounds by source, all spiders with status indicators, quick-action "Run Now" buttons, last sync timestamps
- `frontend/src/pages/admin/ScrapersPage.jsx` — spider list with:
  - Enable/disable toggle per spider
  - Schedule selector (manual, daily, weekly, monthly)
  - Target states multi-select (or "All US")
  - Item limit input (10, 50, 100, unlimited)
  - "Run Now" button per spider
  - Status badge: idle / running (with elapsed time) / completed / failed
  - Last run stats: items found, loaded, errors, duration
- `frontend/src/pages/admin/RunHistoryPage.jsx` — paginated table of all runs with filters
- `frontend/src/pages/admin/SpiderDetailPage.jsx` — single spider config + its run history

**Admin components:**
- `frontend/src/components/admin/SpiderCard.jsx` — spider status, last run, quick actions
- `frontend/src/components/admin/RunStatusBadge.jsx` — color-coded status
- `frontend/src/components/admin/ScheduleSelector.jsx` — schedule frequency dropdown
- `frontend/src/components/admin/StateMultiSelect.jsx` — target states picker
- `frontend/src/components/admin/StatsOverview.jsx` — summary cards
- `frontend/src/components/admin/RunHistoryTable.jsx` — sortable/filterable table

**Admin hooks:**
- `frontend/src/hooks/useScraperConfigs.js` — realtime listener on `_scraper_configs`
- `frontend/src/hooks/useScraperRuns.js` — realtime listener on `_scraper_runs` (live status while running)
- `frontend/src/hooks/useAdminActions.js` — wraps Cloud Function calls: `triggerScraper()`, `cancelScraper()`, `updateConfig()`

**Routes (added to App.jsx):**
- `/admin` → DashboardPage
- `/admin/scrapers` → ScrapersPage
- `/admin/scrapers/:name` → SpiderDetailPage
- `/admin/history` → RunHistoryPage
- `/admin/login` → AdminLoginPage

All `/admin/*` routes wrapped in `AdminRoute` guard.

**Cloud Functions for admin API (in `functions/main.py`):**
- `trigger_scraper` (HTTPS callable) — validates super_admin, writes `_scraper_runs` doc, kicks off spider
- `cancel_scraper` (HTTPS callable) — sets run status to "cancelled"
- `update_scraper_config` (HTTPS callable) — updates `_scraper_configs/{spiderName}`
- `get_scraper_dashboard` (HTTPS callable) — returns all configs + recent runs
- `scheduled_scraper_check` (`on_schedule("every 1 hours")`) — checks configs for spiders due to run

**Backend worker:**
- `backend/scripts/run_worker.py` — polls `_scraper_runs` for pending runs, executes Scrapy spiders, updates run doc with stats on completion

### Phase 19: Polish

- `frontend/src/pages/NotFoundPage.jsx` — 404
- `frontend/src/components/ui/BackToTop.jsx`
- Responsive testing, error boundaries, loading states

---

## Firestore Schema

### Collection: `campgrounds`

```
campgrounds (collection)
└── {campgroundId} (document)    # ID = "{source}_{sourceId}"
    ├── name: string
    ├── slug: string
    ├── description: string
    ├── source: string           # "recreation_gov" | "nps" | "koa" | "hipcamp" | "good_sam" | "thousand_trails" | "state_parks"
    ├── sourceId: string
    │
    ├── location: map
    │   ├── address: string
    │   ├── city: string
    │   ├── state: string        # 2-letter code "AZ"
    │   ├── stateFullName: string
    │   ├── zip: string
    │   ├── county: string
    │   ├── geopoint: GeoPoint
    │   ├── latitude: number
    │   ├── longitude: number
    │   ├── region: string       # "Southwest", "Pacific Northwest", etc.
    │   └── nearestCity: string
    │
    ├── contact: map
    │   ├── phone: string
    │   ├── email: string
    │   ├── website: string
    │   └── reservationUrl: string
    │
    ├── details: map
    │   ├── totalSites: number
    │   ├── siteTypes: array<string>
    │   ├── maxRvLength: number
    │   ├── elevation: number
    │   ├── season: string
    │   ├── reservationType: string
    │   ├── priceRange: map { min, max }
    │   ├── managedBy: string
    │   └── parkName: string
    │
    ├── amenities: map
    │   ├── hookups: array<string>
    │   ├── facilities: array<string>
    │   ├── activities: array<string>
    │   ├── accessibility: boolean
    │   ├── petsAllowed: boolean
    │   └── cellService: string
    │
    ├── photos: array<map>
    │   ├── url: string
    │   ├── caption: string
    │   └── source: string
    │
    ├── ratings: map
    │   ├── avgRating: number
    │   ├── totalReviews: number
    │   └── sourceRating: number
    │
    └── metadata: map
        ├── createdAt: timestamp
        ├── updatedAt: timestamp
        ├── lastSourceSync: timestamp
        ├── isVerified: boolean
        └── isActive: boolean
```

### Subcollection: `campgrounds/{campgroundId}/reviews`

```
reviews (subcollection)
└── {reviewId}
    ├── userId: string
    ├── userName: string
    ├── rating: number (1-5)
    ├── title: string
    ├── text: string
    ├── visitDate: timestamp
    ├── photos: array<string>
    ├── helpfulCount: number
    ├── tags: array<string>
    └── createdAt: timestamp
```

### Admin Collections

```
_scraper_configs (collection)
└── {spiderName} (document)          # e.g., "koa", "hipcamp", "recreation_gov"
    ├── enabled: boolean
    ├── schedule: string             # "manual" | "daily" | "weekly" | "monthly"
    ├── targetStates: array<string>  # ["CA","CO"] or null (all states)
    ├── itemLimit: number            # null = unlimited
    ├── lastRunAt: timestamp
    ├── lastRunStatus: string        # "success" | "failed" | "running"
    └── lastRunStats: map
        ├── itemsFound: number
        ├── itemsLoaded: number
        ├── errors: number
        └── durationSeconds: number

_scraper_runs (collection)
└── {runId} (document)
    ├── spiderName: string
    ├── status: string               # "pending" | "running" | "completed" | "failed" | "cancelled"
    ├── startedAt: timestamp
    ├── completedAt: timestamp
    ├── triggeredBy: string          # userId of admin who triggered it
    ├── config: map                  # snapshot of config used for this run
    │   ├── targetStates: array
    │   └── itemLimit: number
    ├── stats: map
    │   ├── itemsFound: number
    │   ├── itemsLoaded: number
    │   ├── errors: number
    │   └── durationSeconds: number
    └── errorLog: array<string>      # error messages from the run
```

---

## Key Design Decisions

**Pipeline + Scrapers:**
1. **Document ID:** `{source}_{sourceId}` (e.g., `recreation_gov_232447`, `koa_yosemite-pines`)
2. **Merge strategy:** `set(merge=True)` — never overwrites `ratings` or `metadata.createdAt`
3. **Dedup priority:** NPS > Recreation.gov > KOA > Hipcamp > Good Sam > Thousand Trails > state_parks
4. **Stale handling:** Soft-delete (`metadata.isActive = False`), never hard-delete
5. **Rate limiting:** 0.5s for RIDB, NPS 1,000 req/hr, scrapers use Scrapy autothrottle + 2s delay
6. **Scrapy ethics:** `ROBOTSTXT_OBEY = True`, conservative concurrency (4), autothrottle enabled, fake user agent rotation
7. **Source field values:** `"recreation_gov"`, `"nps"`, `"koa"`, `"hipcamp"`, `"good_sam"`, `"thousand_trails"`, `"state_parks"`
8. **Collections:** `campgrounds` (public catalog from pipeline) is separate from `campgrounds_registry` (app-internal operational data)

**Frontend:**
9. **Read-only public pages:** Frontend only reads from `campgrounds`, never writes
10. **Pagination:** Cursor-based, 24 items/page
11. **Filtering:** One `array-contains` server-side, additional filters client-side
12. **Search:** Prefix range query on `name`
13. **Maps:** Leaflet + OpenStreetMap (free, no API key), clustered markers
14. **Code splitting:** React.lazy for MapPage/CampgroundPage/admin pages
15. **Caching:** Firestore persistent local cache

**Admin Dashboard:**
16. **Auth:** Firebase Auth, checks `users/{uid}.role == 'super_admin'` (reuses existing role system from firestore.rules)
17. **Execution model:** Admin UI → Cloud Function → writes `_scraper_runs` doc → backend worker polls and executes spider → updates run doc with stats
18. **Realtime monitoring:** Admin uses Firestore `onSnapshot` listeners for live spider status updates
19. **Config persistence:** Spider settings in `_scraper_configs/{spiderName}`, editable from UI, survives deployments

---

## Environment Variables (.env)

```
RECREATION_GOV_API_KEY=your_ridb_api_key_here
NPS_API_KEY=your_nps_api_key_here
GOOGLE_PLACES_API_KEY=your_key_here (optional)
FIREBASE_PROJECT_ID=hcp-social-chat-firebase-host
FIREBASE_SERVICE_ACCOUNT_PATH=./service-account.json
LOG_LEVEL=INFO
```

---

## Verification Plan

### Backend — API Pipeline
1. `cd backend && pip install -r requirements.txt`
2. Create `.env` from `.env.example` with API keys
3. `python scripts/run_single_source.py recreation_gov --limit 5`
4. Verify sample JSON matches schema
5. `python scripts/run_single_source.py recreation_gov --limit 5 --load`
6. Check Firebase Console for 5 docs in `campgrounds`
7. Repeat for NPS: `python scripts/run_single_source.py nps --limit 5 --load`
8. `python -m pytest tests/ -v`

### Backend — Scrapers
9. `cd backend && scrapy list` (from `scrapers/` dir) — verify all spiders visible
10. `python scripts/run_scraper.py koa --limit 5` — test KOA spider
11. Verify scraped data normalizes to unified schema
12. `python scripts/run_scraper.py koa --limit 5 --load` — write to Firestore
13. Repeat for each spider

### Backend — Full Sync
14. `python scripts/run_full_sync.py --dry-run` — verify end-to-end without writes
15. `python scripts/run_full_sync.py` — full pipeline run

### Frontend — Public Pages
16. `cd frontend && npm install && npm run dev`
17. Verify home page loads with campground cards from Firestore
18. Test browse by state, region, filters, search
19. Test detail page (photos, amenities, mini map, reservation link)
20. Test map page (markers, clustering, popups)
21. Test mobile responsiveness

### Frontend — Admin Dashboard
22. Navigate to `/admin` — verify redirect to login
23. Sign in as super_admin user — verify dashboard loads
24. Verify spider cards show all 7 sources with configs
25. Test "Run Now" on a spider — verify status updates to "running" in realtime
26. Test schedule/state/limit config changes — verify saved to `_scraper_configs`
27. Test run history page — verify past runs with stats
28. Sign in as non-admin — verify "Access Denied" on `/admin`

### Deploy
29. `npm run build` then `firebase deploy --only hosting`
30. `firebase deploy --only functions`
31. `firebase deploy --only firestore` — deploy rules + indexes
