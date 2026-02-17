# Campfire Campgrounds — Backend Data Pipeline

Python-based data pipeline that gathers US campground data from public APIs and web scrapers, normalizes it into a unified schema, and loads it into Firestore.

## Data Sources

| Source | Type | Est. Records | Rate Limit |
|--------|------|-------------|------------|
| Recreation.gov (RIDB) | API | ~3,500 | 0.5s delay |
| NPS API | API | ~500 | 1.0s delay |
| KOA | Scraper | ~500 | 2s + autothrottle |
| Hipcamp | Scraper | ~1,000+ | 2s + autothrottle |
| Good Sam | Scraper | ~2,000+ | 2s + autothrottle |
| Thousand Trails | Scraper | ~80 | 2s + autothrottle |
| State Parks | Scraper | varies | 2s + autothrottle |

## Setup

```bash
cd backend
pip install -r requirements.txt

# Copy and fill in API keys
cp .env.example .env
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RECREATION_GOV_API_KEY` | Yes | RIDB API key from recreation.gov |
| `NPS_API_KEY` | Yes | NPS Developer API key |
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `GOOGLE_PLACES_API_KEY` | No | For future Google Places enrichment |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | No | Path to service account JSON (uses ADC if not set) |

## Usage

### Single Source (testing)

```bash
# Fetch 5 records from Recreation.gov (no Firestore write)
python scripts/run_single_source.py recreation_gov --limit 5

# Fetch and load 10 NPS records to Firestore
python scripts/run_single_source.py nps --limit 10 --load

# Dry run (logs what would happen)
python scripts/run_single_source.py recreation_gov --limit 5 --dry-run
```

### Run a Spider

```bash
# Run KOA spider with limit
python scripts/run_scraper.py koa --limit 10

# Run with state filter
python scripts/run_scraper.py good_sam --states CA,CO,TX --limit 50

# Dry run
python scripts/run_scraper.py hipcamp --dry-run
```

### Full Sync

```bash
# Dry run — all sources
python scripts/run_full_sync.py --dry-run

# Full pipeline (APIs + scrapers + dedup + load)
python scripts/run_full_sync.py

# Skip scrapers (APIs only)
python scripts/run_full_sync.py --skip-scrapers
```

### Background Worker (for admin dashboard)

```bash
# Polls Firestore for pending scraper runs
python scripts/run_worker.py
```

## Architecture

```
backend/
├── config/          # Settings, API keys, region mappings
├── sources/         # API clients (Recreation.gov, NPS)
├── scrapers/        # Scrapy project with 5 spiders
├── transforms/      # Normalizer, geocoder, deduplicator
├── loaders/         # Firestore batch writer
├── scripts/         # CLI entry points
└── tests/           # pytest test suite
```

### Pipeline Flow

1. **Fetch** — API clients paginate through Recreation.gov/NPS; Scrapy spiders crawl private sites
2. **Normalize** — All records mapped to unified Firestore schema with `_doc_id = {source}_{sourceId}`
3. **Deduplicate** — Cross-source fuzzy matching (name similarity >= 0.85 + distance <= 0.5 mi)
4. **Load** — Batch upsert with `set(merge=True)`; protects `ratings` and `metadata.createdAt`
5. **Cleanup** — Soft-delete stale records (`metadata.isActive = False`)

### Firestore Document Schema

```
campgrounds/{source}_{sourceId}
├── name, slug
├── location: { address, city, state, zipCode, latitude, longitude, region }
├── contact: { phone, email, website, reservationUrl }
├── details: { description, totalSites, siteTypes[], maxRvLength, ... }
├── amenities: { hookups[], facilities[], activities[], petsAllowed, ... }
├── photos: [{ url, caption }]
├── ratings: { average: 0, count: 0 }
└── metadata: { source, sourceId, isActive, createdAt, updatedAt }
```

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Deduplication Priority

When the same campground appears in multiple sources, data is merged with this priority (highest first):

1. NPS
2. Recreation.gov
3. KOA
4. Hipcamp
5. Good Sam
6. Thousand Trails
7. State Parks
