"""Configuration loading for the Capitol Signal POC.

Leaf module: no project imports. Provides a stdlib-only .env loader (python-dotenv
is not installed) and a load_config function that overlays os.environ on the file.
"""

from dataclasses import dataclass
import os


@dataclass
class Config:
    slack_webhook_url: str | None
    dry_run: bool
    min_amount: int
    require_ticker: bool
    watchlist: list
    capitol_api_url: str
    capitol_api_cache: str | None


def load_env_file(path) -> dict:
    """Parse KEY=VALUE lines from a .env file.

    Ignore blank lines and lines starting with #. Strip surrounding whitespace
    and matching surrounding quotes from values. A missing file yields {}.
    """
    result = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except FileNotFoundError:
        return {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[key] = value
    return result


def _to_bool(value, default) -> bool:
    """Interpret a string flag. Missing value uses default. A value in the
    falsey set maps to False, anything else maps to True.
    """
    if value is None:
        return default
    if value.strip().lower() in ("0", "false", "no", ""):
        return False
    return True


def _to_int(value, default) -> int:
    """Interpret a string as int, tolerating None and bad values by using default."""
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def _parse_watchlist(value) -> list:
    """Split a comma separated watchlist, strip, lowercase, drop empties."""
    if not value:
        return []
    items = []
    for part in value.split(","):
        token = part.strip().lower()
        if token:
            items.append(token)
    return items


def load_config(env_path=".env") -> Config:
    """Read the env file then overlay os.environ (os.environ wins)."""
    file_env = load_env_file(env_path)

    def get(key):
        if key in os.environ:
            return os.environ[key]
        return file_env.get(key)

    dry_run = _to_bool(get("DRY_RUN"), True)
    min_amount = _to_int(get("MIN_AMOUNT"), 0)
    require_ticker = _to_bool(get("REQUIRE_TICKER"), True)
    watchlist = _parse_watchlist(get("WATCHLIST"))

    capitol_api_url = get("CAPITOL_API_URL")
    if not capitol_api_url:
        capitol_api_url = "http://localhost:3000"

    capitol_api_cache = get("CAPITOL_API_CACHE")
    slack_webhook_url = get("SLACK_WEBHOOK_URL")

    return Config(
        slack_webhook_url=slack_webhook_url,
        dry_run=dry_run,
        min_amount=min_amount,
        require_ticker=require_ticker,
        watchlist=watchlist,
        capitol_api_url=capitol_api_url,
        capitol_api_cache=capitol_api_cache,
    )
