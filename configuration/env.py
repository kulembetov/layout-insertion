# pyright: strict
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class FigmaSettings:
    """Настройки, приходящие из окружения."""

    FIGMA_FILE_ID: str
    FIGMA_TOKEN: str

    @staticmethod
    def from_env() -> FigmaSettings:
        load_dotenv()
        return FigmaSettings(
            FIGMA_FILE_ID=os.environ.get("FIGMA_FILE_ID", ""),
            FIGMA_TOKEN=os.environ.get("FIGMA_TOKEN", ""),
        )


figma_settings: Final[FigmaSettings] = FigmaSettings.from_env()
