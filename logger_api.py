"""FastAPI service that tracks how many times the HDB Ops Survey Report
generator has been used, and the resulting hours saved.

Run standalone with:
    uv run uvicorn logger_api:app --reload --port 8000

The Streamlit app (see streamlit_app.py, LOGGER_URL) POSTs to /usage each
time a report is generated, and GETs /usage to display the running totals
without recording a new use.
"""

import json
import threading
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="HDB Ops Survey Report - Usage Logger")

DATA_FILE = Path(__file__).parent / "usage_data.json"
MINUTES_SAVED_PER_USE = 15
_lock = threading.Lock()


class UsageStats(BaseModel):
    count: int
    minutes_saved: int
    hours_saved: float


def _read_count() -> int:
    if not DATA_FILE.exists():
        return 0
    return json.loads(DATA_FILE.read_text()).get("count", 0)


def _write_count(count: int) -> None:
    DATA_FILE.write_text(json.dumps({"count": count}))


def _stats(count: int) -> UsageStats:
    minutes_saved = count * MINUTES_SAVED_PER_USE
    return UsageStats(count=count, minutes_saved=minutes_saved, hours_saved=round(minutes_saved / 60, 2))


@app.post("/usage", response_model=UsageStats)
def log_usage() -> UsageStats:
    """Record one use of the report generator and return the updated totals."""
    with _lock:
        count = _read_count() + 1
        _write_count(count)
    return _stats(count)


@app.get("/usage", response_model=UsageStats)
def get_usage() -> UsageStats:
    """Return the current usage totals without incrementing them."""
    with _lock:
        count = _read_count()
    return _stats(count)
