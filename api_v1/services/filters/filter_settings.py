from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LegacyFilterMode(Enum):
    ALL = "all"
    SPECIFIC_SLIDES = "specific_slides"
    SPECIFIC_BLOCKS = "specific_blocks"
    BY_TYPE = "by_type"
    READY_TO_DEV = "ready_to_dev"


@dataclass
class LegacyFilterConfig:
    mode: LegacyFilterMode = LegacyFilterMode.ALL
    target_slides: list[int] = field(default_factory=list)
    target_block_types: list[str] = field(default_factory=list)
    target_containers: list[str] = field(default_factory=list)
    require_z_index: bool = True
    min_area: int = 0
    exclude_hidden: bool = True
    ready_to_dev_marker: Optional[str] = None  # marker for 'ready to dev' (e.g., '[ready]')


class FilterMode(Enum):
    ALL = "all"
    SLIDE_GROUP = "slide_group"
    SLIDE_NAME = "slide_name"
    STATUS = "status"


@dataclass
class FilterConfig:
    mode: LegacyFilterMode = LegacyFilterMode.ALL
    target_slides: list[int] = field(default_factory=list) # SLIDE_GROUP
    target_names: list[str] = field(default_factory=list) # SLIDE_NAME
    target_statuses: list[str] = field(default_factory=list) # STATUS (['ready_to_dev'])
    require_z_index: bool = True
    min_area: int = 0
    exclude_hidden: bool = True
