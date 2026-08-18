from pathlib import Path

BASE_URL = "https://ghanaeducationdirectory.com"

SEARCH_API_URL = f"{BASE_URL}/search/searchs"

CATEGORY_URL = f"{BASE_URL}/Search/category"

DETAIL_URL_TEMPLATE = f"{BASE_URL}/Search/Details/{{school_id}}"

JHS_CATEGORY = "Junior High School"

DEFAULT_TIMEOUT_SECONDS = 20.0

USER_AGENT = "EduSentrixSchoolMiner/0.1"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INSPECTION_DIR = RAW_DIR / "inspection"

STATE_DIR = DATA_DIR / "state"

STATE_DB_PATH = STATE_DIR / "schoolminer.sqlite3"
