from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedBlock:
    id: str
    figma_type: str
    sql_type: str
    name: str
    dimensions: dict[str, int]
    styles: dict[str, Any]
    slide_number: int
    parent_container: str
    is_target: bool = False
    has_corner_radius: bool = False
    corner_radius: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    text_content: str = None
    figure_info: dict[str, Any] = field(default_factory=dict)
    precompiled_image_info: dict[str, Any] = field(default_factory=dict)

@dataclass
class ExtractedSlide:
    number: int
    container_name: str
    frame_name: str
    slide_type: str
    blocks: list[ExtractedBlock]
    frame_id: str
    dimensions: dict[str, int]
