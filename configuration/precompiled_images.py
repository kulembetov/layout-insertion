# pyright: strict
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class PrecompiledImagesConfig:
    base_url: str
    default_colors: list[str]
    prefix: list[str]


PRECOMPILED_IMAGES: Final[PrecompiledImagesConfig] = PrecompiledImagesConfig(
    base_url="https://storage.yandexcloud.net/presentsimple-dev-s3/layouts/raiffeisen",
    default_colors=[
        "#bae4e4",  # мятно-бирюзовый
        "#c6d6f2",  # холодно-синий
        "#e0e8f5",  # небесно-голубой
        "#e3dcf8",  # сиреневый
        "#f0f0f0",  # светло-серый
        "#f5e7e7",  # розово-бежевый
        "#fce0d2",  # персиково-оранжевый
    ],
    prefix=["Green", "Blue", "Sky", "Purple", "Gray", "Pink", "Orange"],
)
