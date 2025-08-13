from dataclasses import dataclass, field


@dataclass
class ExtractedBlock:
    id: str
    figma_type: str
    sql_type: str
    name: str
    dimensions: dict[str, int]
    styles: dict[str, str | int | float | bool | list]
    slide_number: int
    parent_container: str
    is_target: bool = False
    text_content: str | None = None
    figure_info: dict[str, str | int | float | bool] = field(default_factory=dict)
    precompiled_image_info: dict[str, str | int | float | bool] = field(default_factory=dict)
    comment: str | None = None


@dataclass
class ExtractedSlide:
    number: int
    container_name: str
    frame_name: str
    slide_type: str
    blocks: list[ExtractedBlock]
    frame_id: str
    dimensions: dict[str, int]
    _figma_node: dict | None = None
