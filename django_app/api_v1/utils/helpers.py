import json
from typing import Any

from django_app.api_v1.constants import SLIDES

# ================ Helpful functions ================


def json_dump(obj, filename: str):
    with open(filename, "w", encoding="utf-8") as outfile:
        json.dump(obj, outfile, ensure_ascii=False, indent=4)


def safe_in(item: Any, container) -> bool:
    if not container:
        return False
    return item in container


# =========== !REFACTOR ==================


def round5(value: float) -> int:
    """Round value to nearest 5"""
    return round(value / 5) * 5


def get_slide_number(parent_name: str) -> int:
    """Get slide number from parent container name (case-insensitive, trimmed). Use config.py as the only source of truth."""
    key = parent_name.strip().lower()
    num: int = SLIDES.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, 0)
    if num:
        return num
    raise ValueError(f"Could not find slide number for {key}, parent name: {parent_name}")
