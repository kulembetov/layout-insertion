from dataclasses import dataclass, field
from enum import Enum


class FilterMode(Enum):
    ALL = "all"
    SLIDE_GROUP = "slide_group"
    SLIDE_NAME = "slide_name"
    STATUS = "status"


@dataclass
class FilterConfig:
    mode: FilterMode = FilterMode.ALL
    target_slides: list[int] = field(default_factory=list) # SLIDE_GROUP
    target_names: list[str] = field(default_factory=list) # SLIDE_NAME
    target_statuses: list[str] = field(default_factory=list) # STATUS (['ready_to_dev'])
    require_z_index: bool = True
    min_area: int = 0
    exclude_hidden: bool = True
