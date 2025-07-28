from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FilterMode(Enum):
    ALL = "all"
    SPECIFIC_SLIDES = "specific_slides"
    SPECIFIC_BLOCKS = "specific_blocks"
    BY_TYPE = "by_type"


@dataclass
class FilterConfig:
    mode: FilterMode = FilterMode.ALL
    target_slides: list[int] = field(default_factory=list)
    target_block_types: list[str] = field(default_factory=list)
    target_containers: list[str] = field(default_factory=list)
    require_z_index: bool = True
    min_area: int = 0
    exclude_hidden: bool = True
    ready_to_dev_marker: Optional[str] = None  # marker for 'ready to dev' (e.g., '[ready]')
