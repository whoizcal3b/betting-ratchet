import os
from dotenv import load_dotenv

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

AUTH_FILE = os.path.join(BASE_DIR, "auth.json")
DB_FILE = os.path.join(BASE_DIR, "journal.db")
USER_DATA_DIR = os.path.join(BASE_DIR, "chrome_profile")

# Execution Mode: 'PAPER' or 'LIVE'
BOT_MODE = os.getenv("BOT_MODE", "PAPER").upper()

# Mathematical Staking Settings
TARGET_ODDS_MIN = float(os.getenv("TARGET_ODDS_MIN", "2.80"))
DEFAULT_DIVISOR = float(os.getenv("DIVISOR", "10.0"))
INITIAL_BALANCE = float(os.getenv("STARTING_BALANCE", "1000.0"))
RESET_DB_ON_START = os.getenv("RESET_DB_ON_START", "False").lower() in ("true", "1", "yes")

# SportyBet Autonomous Credentials
SPORTYBET_PHONE = os.getenv("SPORTYBET_PHONE", "").strip()
SPORTYBET_PASSWORD = os.getenv("SPORTYBET_PASSWORD", "").strip()

# Telegram Notifications
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_NOTIFY_MILESTONES = os.getenv("TELEGRAM_NOTIFY_MILESTONES", "True").lower() in ("true", "1", "yes")
TELEGRAM_MILESTONE_STEP_PCT = float(os.getenv("TELEGRAM_MILESTONE_STEP_PCT", "100.0"))
TELEGRAM_NOTIFY_BUST = os.getenv("TELEGRAM_NOTIFY_BUST", "True").lower() in ("true", "1", "yes")
TELEGRAM_NOTIFY_ERRORS = os.getenv("TELEGRAM_NOTIFY_ERRORS", "True").lower() in ("true", "1", "yes")

# SportyBet & Platform Settings
SPORTYBET_URL = "https://www.sportybet.com/ng/virtual/"
BRISTOL_PLAYLIST_ID = 23100
BRISTOL_ROUTE = f"#/scheduled/speedway/playlist/{BRISTOL_PLAYLIST_ID}"
WS_ENDPOINT_KEY = "virtual-proxy.virtustec.com/vs"

MIN_BET_LIMIT = 10.0         # SportyBet Nigeria minimum bet limit
MAX_BET_LIMIT = 1000000.0    # SportyBet maximum bet limit

# Automation Settings
HEADLESS = os.getenv("HEADLESS", "True").lower() in ("true", "1", "yes")
MUTE_AUDIO = os.getenv("MUTE_AUDIO", "True").lower() in ("true", "1", "yes")
BLOCK_MEDIA = os.getenv("BLOCK_MEDIA", "True").lower() in ("true", "1", "yes")
BET_WINDOW_SECONDS = 25      # Seconds before race cutoff to execute the bet
BET_CUTOFF_BUFFER = 6        # VirtusTec market closes 5s before race start

# Browser launch arguments
BROWSER_ARGS = [
    "--mute-audio" if MUTE_AUDIO else "--no-default-browser-check",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled"
]
