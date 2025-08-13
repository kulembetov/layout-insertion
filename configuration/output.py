# pyright: strict
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class OutputConfig:
    output_dir: str
    filename_template: str
    timestamp_format: str


OUTPUT_CONFIG: Final[OutputConfig] = OutputConfig(
    output_dir="my_sql_output",
    filename_template="{slide_layout_name}_{timestamp}.sql",
    timestamp_format="%b%d_%H-%M",  # e.g., Mar10_14-23
)
