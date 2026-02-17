"""
Cloud Functions for Campfire Campgrounds.

Provides:
- Scraper control API (trigger, cancel, configure spiders) — super_admin only
- Scheduled API sync (Recreation.gov + NPS)
- Scheduled scraper check (runs spiders based on their configured schedule)
"""

from datetime import datetime, timezone

from firebase_functions import https_fn, scheduler_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app, firestore, auth

set_global_options(max_instances=10)

app = initialize_app()
db = firestore.client(app)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _verify_super_admin(req):
    """Verify the request comes from an authenticated super_admin user.

    For callable functions the ID token is in the Authorization header.
    Returns the decoded token dict on success, raises HttpsError otherwise.
    """
    authorization = req.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.UNAUTHENTICATED,
            message="Missing or invalid Authorization header.",
        )

    id_token = authorization.split("Bearer ")[1]
    try:
        decoded = auth.verify_id_token(id_token)
    except Exception:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.UNAUTHENTICATED,
            message="Invalid ID token.",
        )

    uid = decoded["uid"]
    user_doc = db.collection("users").document(uid).get()
    if not user_doc.exists or user_doc.to_dict().get("role") != "super_admin":
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.PERMISSION_DENIED,
            message="Caller is not a super_admin.",
        )

    return decoded


VALID_SPIDERS = [
    "koa", "hipcamp", "good_sam", "thousand_trails", "state_parks",
]

API_SOURCES = ["recreation_gov", "nps"]


# ---------------------------------------------------------------------------
# 1. trigger_scraper — start a spider run
# ---------------------------------------------------------------------------

@https_fn.on_request()
def trigger_scraper(req: https_fn.Request) -> https_fn.Response:
    """Start a scraper run.

    Body JSON:
        spiderName (str): one of VALID_SPIDERS
        targetStates (list[str] | null): states to scrape, or null for all
        itemLimit (int | null): max items to scrape, or null for unlimited
    """
    import json

    decoded = _verify_super_admin(req)
    body = req.get_json(silent=True) or {}

    spider_name = body.get("spiderName")
    if spider_name not in VALID_SPIDERS:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            message=f"Invalid spider name. Must be one of: {VALID_SPIDERS}",
        )

    now = datetime.now(timezone.utc)
    run_ref = db.collection("_scraper_runs").document()
    run_data = {
        "spiderName": spider_name,
        "status": "pending",
        "startedAt": now,
        "completedAt": None,
        "triggeredBy": decoded["uid"],
        "config": {
            "targetStates": body.get("targetStates"),
            "itemLimit": body.get("itemLimit"),
        },
        "stats": {
            "itemsFound": 0,
            "itemsLoaded": 0,
            "errors": 0,
            "duration": 0,
        },
        "errorLog": [],
    }
    run_ref.set(run_data)

    # Update the spider config with last triggered info
    config_ref = db.collection("_scraper_configs").document(spider_name)
    config_ref.set(
        {
            "lastRunAt": now,
            "lastRunStatus": "running",
        },
        merge=True,
    )

    return https_fn.Response(
        json.dumps({"runId": run_ref.id, "status": "pending"}),
        status=200,
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# 2. cancel_scraper — cancel a running spider
# ---------------------------------------------------------------------------

@https_fn.on_request()
def cancel_scraper(req: https_fn.Request) -> https_fn.Response:
    """Cancel a running scraper run.

    Body JSON:
        runId (str): the _scraper_runs document ID
    """
    import json

    _verify_super_admin(req)
    body = req.get_json(silent=True) or {}

    run_id = body.get("runId")
    if not run_id:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            message="runId is required.",
        )

    run_ref = db.collection("_scraper_runs").document(run_id)
    run_doc = run_ref.get()
    if not run_doc.exists:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.NOT_FOUND,
            message=f"Run {run_id} not found.",
        )

    run_ref.update({
        "status": "cancelled",
        "completedAt": datetime.now(timezone.utc),
    })

    return https_fn.Response(
        json.dumps({"runId": run_id, "status": "cancelled"}),
        status=200,
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# 3. update_scraper_config — update spider configuration
# ---------------------------------------------------------------------------

@https_fn.on_request()
def update_scraper_config(req: https_fn.Request) -> https_fn.Response:
    """Update configuration for a spider.

    Body JSON:
        spiderName (str): one of VALID_SPIDERS
        enabled (bool): whether the spider is enabled
        schedule (str): "manual" | "daily" | "weekly" | "monthly"
        targetStates (list[str] | null): states to target
        itemLimit (int | null): max items per run
    """
    import json

    _verify_super_admin(req)
    body = req.get_json(silent=True) or {}

    spider_name = body.get("spiderName")
    if spider_name not in VALID_SPIDERS:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            message=f"Invalid spider name. Must be one of: {VALID_SPIDERS}",
        )

    allowed_fields = {"enabled", "schedule", "targetStates", "itemLimit"}
    update_data = {k: v for k, v in body.items() if k in allowed_fields}

    if not update_data:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            message="No valid fields to update.",
        )

    config_ref = db.collection("_scraper_configs").document(spider_name)
    config_ref.set(update_data, merge=True)

    return https_fn.Response(
        json.dumps({"spiderName": spider_name, "updated": list(update_data.keys())}),
        status=200,
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# 4. get_scraper_dashboard — return all configs + recent runs
# ---------------------------------------------------------------------------

@https_fn.on_request()
def get_scraper_dashboard(req: https_fn.Request) -> https_fn.Response:
    """Return all spider configs and last 10 runs per spider.

    Avoids N+1 queries from the frontend by bundling everything.
    """
    import json

    _verify_super_admin(req)

    # Fetch all spider configs
    configs = {}
    for doc in db.collection("_scraper_configs").stream():
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

    # Fetch recent runs (last 20 overall, sorted by startedAt desc)
    runs_query = (
        db.collection("_scraper_runs")
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

    return https_fn.Response(
        json.dumps({"configs": configs, "recentRuns": recent_runs}),
        status=200,
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# 5. scheduled_api_sync — run RIDB + NPS sync on schedule
# ---------------------------------------------------------------------------

@scheduler_fn.on_schedule(schedule="every sunday 02:00")
def scheduled_api_sync(event: scheduler_fn.ScheduledEvent) -> None:
    """Weekly sync of Recreation.gov and NPS campground data."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Starting scheduled API sync at %s", datetime.now(timezone.utc))

    now = datetime.now(timezone.utc)

    # Record a run entry for tracking
    run_ref = db.collection("_scraper_runs").document()
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
        import sys
        from pathlib import Path

        backend_root = str(Path(__file__).resolve().parent.parent / "backend")
        if backend_root not in sys.path:
            sys.path.insert(0, backend_root)

        from sources.recreation_gov import RecreationGovSource
        from sources.nps_api import NPSSource
        from transforms.normalizer import normalize_recreation_gov, normalize_nps
        from loaders.firestore_loader import FirestoreLoader

        loader = FirestoreLoader()
        all_records = []

        # Phase 1: Recreation.gov
        logger.info("Fetching Recreation.gov campgrounds...")
        rec_source = RecreationGovSource()
        for facility in rec_source.fetch_all_campgrounds():
            normalized = normalize_recreation_gov(facility)
            all_records.append(normalized)

        # Phase 2: NPS
        logger.info("Fetching NPS campgrounds...")
        nps_source = NPSSource()
        for campground in nps_source.fetch_all_campgrounds():
            normalized = normalize_nps(campground)
            all_records.append(normalized)

        # Phase 3: Load to Firestore
        logger.info("Loading %d records to Firestore...", len(all_records))
        stats = loader.upsert_batch(all_records)

        elapsed = (datetime.now(timezone.utc) - now).total_seconds()
        run_ref.update({
            "status": "completed",
            "completedAt": datetime.now(timezone.utc),
            "stats": {
                "itemsFound": len(all_records),
                "itemsLoaded": stats.get("created", 0) + stats.get("updated", 0),
                "errors": stats.get("failed", 0),
                "duration": elapsed,
            },
        })
        logger.info("API sync completed: %s", stats)

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
    import logging

    logger = logging.getLogger(__name__)
    now = datetime.now(timezone.utc)

    schedule_intervals = {
        "daily": 86400,       # 24 hours
        "weekly": 604800,     # 7 days
        "monthly": 2592000,   # 30 days
    }

    for doc in db.collection("_scraper_configs").stream():
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
        run_ref = db.collection("_scraper_runs").document()
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
        db.collection("_scraper_configs").document(spider_name).update({
            "lastRunAt": now,
            "lastRunStatus": "running",
        })
