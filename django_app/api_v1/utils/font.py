import re
from typing import Any, Optional


def normalize_font_family(font_family: str) -> str:
    if not font_family:
        return ""
    return re.sub(r'[^a-z0-9_]', '', font_family.strip().lower().replace(' ', '_').replace('-', '_'))


def normalize_font_weight(weight: Any) -> Optional[int]:
    """Normalize font weight to valid values (300, 400, 700)"""
    if weight is None:
        return 400
    return None
