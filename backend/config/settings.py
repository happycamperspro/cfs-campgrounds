"""
Central configuration. Loads environment variables from .env,
defines API base URLs, rate limits, Firestore collection names,
and batch size constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# --- API Keys ---
RECREATION_GOV_API_KEY: str = os.getenv("RECREATION_GOV_API_KEY", "")
NPS_API_KEY: str = os.getenv("NPS_API_KEY", "")
GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")

# --- Firebase ---
FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "hcp-social-chat-firebase-host")
FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
FIRESTORE_COLLECTION: str = "campgrounds"

# --- RIDB API ---
RIDB_BASE_URL: str = "https://ridb.recreation.gov/api/v1"
RIDB_PAGE_SIZE: int = 50
RIDB_RATE_LIMIT_DELAY: float = 0.5

# --- NPS API ---
NPS_BASE_URL: str = "https://developer.nps.gov/api/v1"
NPS_PAGE_SIZE: int = 50
NPS_RATE_LIMIT_DELAY: float = 1.0

# --- Pipeline ---
FIRESTORE_BATCH_SIZE: int = 500
RETRY_ATTEMPTS: int = 3
RETRY_BACKOFF_BASE: float = 2.0
DEDUP_DISTANCE_MILES: float = 0.5
DEDUP_NAME_THRESHOLD: float = 0.85

# --- Logging ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
