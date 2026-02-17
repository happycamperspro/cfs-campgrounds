"""
Cloud Functions for Campfire Campgrounds.

Provides:
- Scraper control API (trigger, cancel, configure spiders) — super_admin only
- Scheduled API sync (Recreation.gov + NPS)
- Scheduled scraper check (runs spiders based on their configured schedule)
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

from firebase_functions import https_fn, scheduler_fn
from firebase_functions.options import set_global_options, CorsOptions
from firebase_admin import initialize_app, firestore, auth

set_global_options(max_instances=10)

_cors = CorsOptions(cors_origins="*", cors_methods=["GET", "POST", "OPTIONS"])

app = initialize_app()

logger = logging.getLogger(__name__)

# Lazy Firestore client — avoids blocking module load during deploy analysis
_db = None

def _get_db():
    global _db
    if _db is None:
        _db = firestore.client(app)
    return _db


# ---------------------------------------------------------------------------
# Error / JSON helpers
# ---------------------------------------------------------------------------

def _error(status, message):
    """Return a JSON error response (no exceptions, so CORS headers stay intact)."""
    return https_fn.Response(
        json.dumps({"error": message}),
        status=status,
        content_type="application/json",
    )


def _ok(data):
    """Return a JSON success response."""
    return https_fn.Response(
        json.dumps(data),
        status=200,
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _verify_super_admin(req):
    """Verify the request comes from an authenticated super_admin user.

    Returns (decoded_token, None) on success, or (None, Response) on failure.
    """
    authorization = req.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None, _error(401, "Missing or invalid Authorization header.")

    id_token = authorization.split("Bearer ")[1]
    try:
        decoded = auth.verify_id_token(id_token)
    except Exception:
        return None, _error(401, "Invalid ID token.")

    uid = decoded["uid"]
    user_doc = _get_db().collection("users").document(uid).get()
    if not user_doc.exists or user_doc.to_dict().get("role") != "super_admin":
        return None, _error(403, "Caller is not a super_admin.")

    return decoded, None


VALID_SPIDERS = [
    "koa", "hipcamp", "good_sam", "thousand_trails", "state_parks",
]

ALL_SOURCES = VALID_SPIDERS + ["recreation_gov", "nps"]

API_SOURCES = ["recreation_gov", "nps"]


# ---------------------------------------------------------------------------
# Firestore batch helpers
# ---------------------------------------------------------------------------

def _remove_none_values(d):
    """Recursively remove keys whose values are None from a dict."""
    if not isinstance(d, dict):
        return d
    cleaned = {}
    for key, value in d.items():
        if value is None:
            continue
        if isinstance(value, dict):
            nested = _remove_none_values(value)
            if nested:
                cleaned[key] = nested
        else:
            cleaned[key] = value
    return cleaned


def _batch_upsert_campgrounds(records, run_ref=None):
    """Batch upsert normalized campground records to the campgrounds collection."""
    db = _get_db()
    collection_ref = db.collection("campgrounds")
    batch_size = 500
    loaded = 0

    for i in range(0, len(records), batch_size):
        batch_slice = records[i : i + batch_size]
        batch = db.batch()
        ops = 0

        for record in batch_slice:
            record = dict(record)  # shallow copy
            doc_id = record.pop("_doc_id", None)
            if not doc_id:
                continue
            cleaned = _remove_none_values(record)
            doc_ref = collection_ref.document(doc_id)
            batch.set(doc_ref, cleaned, merge=True)
            ops += 1

        if ops > 0:
            batch.commit()
            loaded += ops

        # Update progress in the run document
        if run_ref:
            run_ref.update({"stats.itemsLoaded": loaded})

    return loaded


# ---------------------------------------------------------------------------
# API source execution
# ---------------------------------------------------------------------------

def _execute_api_source(spider_name, target_states, item_limit, run_ref):
    """Fetch campgrounds from an API source, normalize, and load to Firestore.

    Returns (stats_dict, error_log_list).
    """
    import requests as http
    from normalizer import normalize_nps, normalize_recreation_gov

    start_time = time.time()
    all_records = []
    errors = 0
    error_log = []

    if spider_name == "nps":
        api_key = os.environ.get("NPS_API_KEY", "")
        if not api_key:
            raise RuntimeError("NPS_API_KEY environment variable is not set")

        base_url = "https://developer.nps.gov/api/v1"
        session = http.Session()
        session.headers.update({"X-Api-Key": api_key, "Accept": "application/json"})

        offset = 0
        page_size = 50
        params = {}
        if target_states:
            params["stateCode"] = ",".join(s.upper() for s in target_states)

        while True:
            page_params = {**params, "start": offset, "limit": page_size}
            resp = session.get(
                f"{base_url}/campgrounds", params=page_params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()

            records = data.get("data", [])
            if not records:
                break

            for raw in records:
                try:
                    all_records.append(normalize_nps(raw))
                except Exception as e:
                    errors += 1
                    error_log.append(f"NPS normalize error: {e}")

            # Update progress
            run_ref.update({"stats.itemsFound": len(all_records)})

            if item_limit and len(all_records) >= item_limit:
                all_records = all_records[:item_limit]
                break

            total = int(data.get("total", 0))
            offset += page_size
            if offset >= total:
                break

            time.sleep(1.0)  # Rate limit

    elif spider_name == "recreation_gov":
        api_key = os.environ.get("RECREATION_GOV_API_KEY", "")
        if not api_key:
            raise RuntimeError("RECREATION_GOV_API_KEY environment variable is not set")

        base_url = "https://ridb.recreation.gov/api/v1"
        session = http.Session()
        session.headers.update({"apikey": api_key, "Accept": "application/json"})

        offset = 0
        page_size = 50
        params = {"activity": "CAMPING", "full": "true"}
        if target_states:
            params["state"] = ",".join(s.upper() for s in target_states)

        while True:
            page_params = {**params, "offset": offset, "limit": page_size}
            resp = session.get(
                f"{base_url}/facilities", params=page_params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()

            records = data.get("RECDATA", [])
            if not records:
                break

            for raw in records:
                try:
                    all_records.append(normalize_recreation_gov(raw))
                except Exception as e:
                    errors += 1
                    error_log.append(f"RecGov normalize error: {e}")

            # Update progress
            run_ref.update({"stats.itemsFound": len(all_records)})

            if item_limit and len(all_records) >= item_limit:
                all_records = all_records[:item_limit]
                break

            total_count = (
                data.get("METADATA", {}).get("RESULTS", {}).get("TOTAL_COUNT", 0)
            )
            total = int(total_count)
            offset += page_size
            if offset >= total:
                break

            time.sleep(0.5)  # Rate limit

    # Load to Firestore
    loaded = _batch_upsert_campgrounds(all_records, run_ref)
    elapsed = time.time() - start_time

    stats = {
        "itemsFound": len(all_records),
        "itemsLoaded": loaded,
        "errors": errors,
        "duration": round(elapsed, 1),
    }
    return stats, error_log


# ---------------------------------------------------------------------------
# 1. trigger_scraper — start a spider / API source run
# ---------------------------------------------------------------------------

@https_fn.on_request(cors=_cors, timeout_sec=540, memory=512)
def trigger_scraper(req: https_fn.Request) -> https_fn.Response:
    """Start a scraper run.

    For API sources (nps, recreation_gov): executes the fetch inline and
    returns when complete.  For Scrapy-based spiders: not yet supported
    from Cloud Functions.

    Body JSON:
        spiderName (str): one of ALL_SOURCES
        targetStates (list[str] | null): states to scrape, or null for all
        itemLimit (int | null): max items to scrape, or null for unlimited
    """
    decoded, err = _verify_super_admin(req)
    if err:
        return err

    body = req.get_json(silent=True) or {}

    spider_name = body.get("spiderName")
    if spider_name not in ALL_SOURCES:
        return _error(400, f"Invalid source name. Must be one of: {ALL_SOURCES}")

    target_states = body.get("targetStates")
    item_limit = body.get("itemLimit")
    if item_limit:
        try:
            item_limit = int(item_limit)
        except (ValueError, TypeError):
            item_limit = None

    now = datetime.now(timezone.utc)
    run_ref = _get_db().collection("_scraper_runs").document()
    config_ref = _get_db().collection("_scraper_configs").document(spider_name)

    if spider_name in API_SOURCES:
        # ---- Execute API source inline ----
        run_ref.set({
            "spiderName": spider_name,
            "status": "running",
            "startedAt": now,
            "completedAt": None,
            "triggeredBy": decoded["uid"],
            "config": {
                "targetStates": target_states,
                "itemLimit": item_limit,
            },
            "stats": {
                "itemsFound": 0,
                "itemsLoaded": 0,
                "errors": 0,
                "duration": 0,
            },
            "errorLog": [],
        })
        config_ref.set(
            {"lastRunAt": now, "lastRunStatus": "running"}, merge=True
        )

        try:
            stats, error_log = _execute_api_source(
                spider_name, target_states, item_limit, run_ref
            )
            completed_at = datetime.now(timezone.utc)
            run_ref.update({
                "status": "completed",
                "completedAt": completed_at,
                "stats": stats,
                "errorLog": error_log[:50],
            })
            config_ref.update({"lastRunStatus": "completed"})

            return _ok({
                "runId": run_ref.id,
                "status": "completed",
                "stats": stats,
            })

        except Exception as e:
            logger.exception("API source execution failed: %s", e)
            completed_at = datetime.now(timezone.utc)
            run_ref.update({
                "status": "failed",
                "completedAt": completed_at,
                "errorLog": firestore.ArrayUnion([str(e)]),
            })
            config_ref.update({"lastRunStatus": "failed"})

            return _ok({
                "runId": run_ref.id,
                "status": "failed",
                "error": str(e),
            })

    else:
        # ---- Scrapy spiders — not yet supported in Cloud Functions ----
        run_ref.set({
            "spiderName": spider_name,
            "status": "failed",
            "startedAt": now,
            "completedAt": now,
            "triggeredBy": decoded["uid"],
            "config": {
                "targetStates": target_states,
                "itemLimit": item_limit,
            },
            "stats": {
                "itemsFound": 0,
                "itemsLoaded": 0,
                "errors": 1,
                "duration": 0,
            },
            "errorLog": [
                "Scrapy-based spiders are not yet supported for on-demand "
                "runs from the dashboard. Use the CLI worker instead."
            ],
        })
        config_ref.set(
            {"lastRunAt": now, "lastRunStatus": "failed"}, merge=True
        )

        return _ok({
            "runId": run_ref.id,
            "status": "failed",
            "error": "Scrapy spiders cannot run from the dashboard yet.",
        })


# ---------------------------------------------------------------------------
# 2. cancel_scraper — cancel a running spider
# ---------------------------------------------------------------------------

@https_fn.on_request(cors=_cors)
def cancel_scraper(req: https_fn.Request) -> https_fn.Response:
    """Cancel a running scraper run.

    Body JSON:
        runId (str): the _scraper_runs document ID
    """
    _, err = _verify_super_admin(req)
    if err:
        return err

    body = req.get_json(silent=True) or {}

    run_id = body.get("runId")
    if not run_id:
        return _error(400, "runId is required.")

    run_ref = _get_db().collection("_scraper_runs").document(run_id)
    run_doc = run_ref.get()
    if not run_doc.exists:
        return _error(404, f"Run {run_id} not found.")

    run_ref.update({
        "status": "cancelled",
        "completedAt": datetime.now(timezone.utc),
    })

    return _ok({"runId": run_id, "status": "cancelled"})


# ---------------------------------------------------------------------------
# 3. update_scraper_config — update spider configuration
# ---------------------------------------------------------------------------

@https_fn.on_request(cors=_cors)
def update_scraper_config(req: https_fn.Request) -> https_fn.Response:
    """Update configuration for a source.

    Body JSON:
        spiderName (str): one of ALL_SOURCES
        enabled (bool): whether the source is enabled
        schedule (str): "manual" | "daily" | "weekly" | "monthly"
        targetStates (list[str] | null): states to target
        itemLimit (int | null): max items per run
    """
    _, err = _verify_super_admin(req)
    if err:
        return err

    body = req.get_json(silent=True) or {}

    spider_name = body.get("spiderName")
    if spider_name not in ALL_SOURCES:
        return _error(400, f"Invalid source name. Must be one of: {ALL_SOURCES}")

    allowed_fields = {"enabled", "schedule", "targetStates", "itemLimit"}
    update_data = {k: v for k, v in body.items() if k in allowed_fields}

    if not update_data:
        return _error(400, "No valid fields to update.")

    config_ref = _get_db().collection("_scraper_configs").document(spider_name)
    config_ref.set(update_data, merge=True)

    return _ok({"spiderName": spider_name, "updated": list(update_data.keys())})


# ---------------------------------------------------------------------------
# 4. get_scraper_dashboard — return all configs + recent runs
# ---------------------------------------------------------------------------

@https_fn.on_request(cors=_cors)
def get_scraper_dashboard(req: https_fn.Request) -> https_fn.Response:
    """Return all spider configs and last 10 runs per spider.

    Avoids N+1 queries from the frontend by bundling everything.
    """
    _, err = _verify_super_admin(req)
    if err:
        return err

    # Fetch all spider configs
    configs = {}
    for doc in _get_db().collection("_scraper_configs").stream():
        configs[doc.id] = doc.to_dict()

    # Ensure all spiders have a config entry
    for spider in VALID_SPIDERS:
        if spider not in configs:
            configs[spider] = {
                "enabled": False,
                "schedule": "manual",
                "targetStates": None,
                "itemLimit": None,
                "lastRunAt": None,
                "lastRunStatus": None,
                "lastRunStats": None,
            }

    # Add API sources info
    for source in API_SOURCES:
        if source not in configs:
            configs[source] = {
                "enabled": True,
                "schedule": "weekly",
                "type": "api",
                "lastRunAt": None,
                "lastRunStatus": None,
            }

    # Fetch recent runs (last 50 overall, sorted by startedAt desc)
    runs_query = (
        _get_db().collection("_scraper_runs")
        .order_by("startedAt", direction=firestore.Query.DESCENDING)
        .limit(50)
    )
    recent_runs = []
    for doc in runs_query.stream():
        run = doc.to_dict()
        run["runId"] = doc.id
        # Convert timestamps to ISO strings for JSON serialization
        for ts_field in ("startedAt", "completedAt"):
            if run.get(ts_field):
                run[ts_field] = run[ts_field].isoformat()
        recent_runs.append(run)

    # Convert config timestamps too
    for name, config in configs.items():
        if config.get("lastRunAt"):
            config["lastRunAt"] = config["lastRunAt"].isoformat()

    return _ok({"configs": configs, "recentRuns": recent_runs})


# ---------------------------------------------------------------------------
# 5. scheduled_api_sync — run RIDB + NPS sync on schedule
# ---------------------------------------------------------------------------

@scheduler_fn.on_schedule(schedule="every sunday 02:00", timeout_sec=540, memory=512)
def scheduled_api_sync(event: scheduler_fn.ScheduledEvent) -> None:
    """Weekly sync of Recreation.gov and NPS campground data."""
    logger.info("Starting scheduled API sync at %s", datetime.now(timezone.utc))

    now = datetime.now(timezone.utc)

    # Record a run entry for tracking
    run_ref = _get_db().collection("_scraper_runs").document()
    run_ref.set({
        "spiderName": "api_sync",
        "status": "running",
        "startedAt": now,
        "completedAt": None,
        "triggeredBy": "scheduler",
        "config": {},
        "stats": {"itemsFound": 0, "itemsLoaded": 0, "errors": 0, "duration": 0},
        "errorLog": [],
    })

    try:
        total_stats = {"itemsFound": 0, "itemsLoaded": 0, "errors": 0}
        all_errors = []

        for source_name in ["recreation_gov", "nps"]:
            stats, error_log = _execute_api_source(
                source_name, None, None, run_ref
            )
            total_stats["itemsFound"] += stats["itemsFound"]
            total_stats["itemsLoaded"] += stats["itemsLoaded"]
            total_stats["errors"] += stats["errors"]
            all_errors.extend(error_log)

        elapsed = (datetime.now(timezone.utc) - now).total_seconds()
        total_stats["duration"] = round(elapsed, 1)

        run_ref.update({
            "status": "completed",
            "completedAt": datetime.now(timezone.utc),
            "stats": total_stats,
            "errorLog": all_errors[:50],
        })
        logger.info("API sync completed: %s", total_stats)

    except Exception as e:
        logger.exception("API sync failed: %s", e)
        run_ref.update({
            "status": "failed",
            "completedAt": datetime.now(timezone.utc),
            "errorLog": firestore.ArrayUnion([str(e)]),
        })


# ---------------------------------------------------------------------------
# 6. scheduled_scraper_check — check for spiders due to run
# ---------------------------------------------------------------------------

@scheduler_fn.on_schedule(schedule="every 1 hours")
def scheduled_scraper_check(event: scheduler_fn.ScheduledEvent) -> None:
    """Check _scraper_configs for spiders due to run based on schedule."""
    now = datetime.now(timezone.utc)

    schedule_intervals = {
        "daily": 86400,       # 24 hours
        "weekly": 604800,     # 7 days
        "monthly": 2592000,   # 30 days
    }

    for doc in _get_db().collection("_scraper_configs").stream():
        config = doc.to_dict()
        spider_name = doc.id

        if not config.get("enabled", False):
            continue

        schedule = config.get("schedule", "manual")
        if schedule == "manual":
            continue

        interval = schedule_intervals.get(schedule)
        if not interval:
            continue

        last_run = config.get("lastRunAt")
        if last_run:
            elapsed = (now - last_run).total_seconds()
            if elapsed < interval:
                continue

        # Spider is due — create a pending run
        logger.info("Spider '%s' is due for scheduled run.", spider_name)
        run_ref = _get_db().collection("_scraper_runs").document()
        run_ref.set({
            "spiderName": spider_name,
            "status": "pending",
            "startedAt": now,
            "completedAt": None,
            "triggeredBy": "scheduler",
            "config": {
                "targetStates": config.get("targetStates"),
                "itemLimit": config.get("itemLimit"),
            },
            "stats": {
                "itemsFound": 0,
                "itemsLoaded": 0,
                "errors": 0,
                "duration": 0,
            },
            "errorLog": [],
        })

        # Update config
        _get_db().collection("_scraper_configs").document(spider_name).update({
            "lastRunAt": now,
            "lastRunStatus": "running",
        })
