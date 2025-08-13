# pyright: strict
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from configuration.types import Dimensions, SlideLayoutType

MINIATURES_BASE_PATH: Final[str] = "https://storage.yandexcloud.net/presentsimple-dev-s3/layouts/business/miniatures"
DEFAULT_COLOR_SETTINGS_ID: Final[str] = "019565bd-99ce-792c-86fd-0188712beb9b"
DEFAULT_COLOR: Final[str] = "#ffffff"
MINIATURE_EXTENSION: Final[str] = ".png"


@dataclass(frozen=True, slots=True)
class DefaultValues:
    slide_layout_name: str
    slide_layout_number: int
    presentation_layout_id: str
    slide_layout_type: str
    num_blocks: int


DEFAULT_VALUES: Final[DefaultValues] = DefaultValues(
    slide_layout_name="grid_cards_horizontal",
    slide_layout_number=9,
    presentation_layout_id="01989db8-b17d-78ec-b9d6-04e42c8bede2",
    slide_layout_type=str(SlideLayoutType.classic),
    num_blocks=5,
)

# Default values for new tables
SLIDE_LAYOUT_ADDITIONAL_INFO: Final[dict[str, object]] = {
    "percentesCount": 0,
    "maxSymbolsInBlock": 0,
    "hasHeaders": False,
    "type": str(SlideLayoutType.classic),
    "infographicsType": None,
}

SLIDE_LAYOUT_DIMENSIONS: Final[Dimensions] = Dimensions(x=0, y=0, w=1200, h=675)
