import json
import os
import re
from collections.abc import Sequence
from typing import Any

import uuid_utils as uuid

import configuration as config


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


def extract_frame_data(data: dict) -> list[dict]:
    """Recursive extraction from cache."""
    results = []

    def recursive_extract(obj):
        nonlocal results

        if isinstance(obj, dict):
            if all(key in obj for key in ["slide_number", "frame_name", "imagesCount", "sentences", "forGeneration", "slide_type", "dimensions", "columns", "presentationPaletteColors", "slideConfig"]):
                result_dict = {
                    "number": obj.get("slide_number"),
                    "name": obj.get("frame_name").split()[0],
                    "imagesCount": obj.get("imagesCount"),
                    "sentences": obj.get("sentences"),
                    "forGeneration": obj.get("forGeneration"),
                    "isLast": obj.get("slide_type"),
                    "dimensions": obj.get("dimensions"),
                    "blocks": obj.get("blocks"),
                    "slide_type": obj.get("slide_type"),
                    "columns": obj.get("columns"),
                    "presentationPaletteColors": obj.get("presentationPaletteColors"),
                    "slideConfig": obj.get("slideConfig"),
                }
                results.append(result_dict)

            for value in obj.values():
                recursive_extract(value)

        elif isinstance(obj, list):
            for item in obj:
                recursive_extract(item)

    recursive_extract(data)
    return results


def add_frame_data(data: list[dict[Any, Any]], presentation_layout_id: str) -> list[dict[Any, Any]]:
    """Add extra fields."""

    for item in data:
        if item["isLast"] == "last":
            item.update(
                {
                    "isLast": True,
                }
            )
        else:
            item.update(
                {
                    "isLast": False,
                }
            )
        item.update({"presentationLayoutId": presentation_layout_id, "maxTokensPerBlock": 300, "maxWordsPerSentence": 15, "minWordsPerSentence": 10, "forGeneration": True, "isActive": True, "presentationLayoutIndexColor": 0})
    return data


def get_slide_layout_data_from_cache(presentation_layout_id: str) -> list[dict[Any, Any]]:
    """Get slide layout data from cahce."""

    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    json_file_path = os.path.join(parent_dir, "output.json")
    with open(json_file_path, encoding="utf-8") as file:
        cache = json.load(file)

    # FIGMA_FILE_ID = os.getenv("FIGMA_FILE_ID")
    # cache = get_cached_request(FIGMA_FILE_ID)
    slide_layout_frame_data = extract_frame_data(cache)
    slide_layout_frame_data = add_frame_data(slide_layout_frame_data, presentation_layout_id=presentation_layout_id)
    return slide_layout_frame_data


class SlideLayoutUtils:
    """Slide Layout Utils."""

    def __init__(self):
        self.miniatures_base_path = config.MINIATURES_BASE_PATH
        self.slide_nimber_to_path = config.SLIDE_NUMBER_TO_TYPE
        self.slide_number_to_number = config.SLIDE_NUMBER_TO_NUMBER
        self.miniature_extension = config.MINIATURE_EXTENSION

    def build_slide_icon_url(self, slide_type: str, slide_name: str, columns: int | None) -> str:
        """Generate icon URL for slide layout."""
        # Slide types that should NOT have numbers in their miniature paths
        skip_slides_type = {"infographics", "chart", "table", "title", "last"}

        miniature_folder = self._camel_to_snake(slide_type)

        # If this slide type should skip numbering or no columns provided, return without number
        if slide_type in skip_slides_type or columns is None:
            return f"{self.miniatures_base_path}/{miniature_folder}/{slide_name}{self.miniature_extension}"

        # For slides with columns, use the column number directly in the path
        return f"{self.miniatures_base_path}/{miniature_folder}/{columns}_{slide_name}{self.miniature_extension}"

    def _camel_to_snake(self, name):
        """Convert camelCase or PascalCase to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class BlockLayoutUtils:
    """Block Layout Utils."""

    def __init__(self):
        self.miniatures_base_path = config.MINIATURES_BASE_PATH

    def normalize_name(self, name: str) -> str:
        """
        Normalize a block or slide name using centralized cleaning rules.
        """
        return DataCleaner.clean_block_name(name)

    # def extract_index(self, name: str, block_type: str | None = None) -> int | None:
    #     """
    #     Extracts an index from a block name using all known patterns.
    #     """
    #     return DataCleaner.extract_index(name, block_type)


class CleaningRule:
    """Base class for cleaning rules."""

    def apply(self, text: str) -> str:
        """Apply the cleaning rule to the text."""
        raise NotImplementedError


class RegexCleaningRule(CleaningRule):
    """Cleaning rule that uses regex substitution."""

    def __init__(self, pattern: str, replacement: str = "", flags: int = 0):
        self.pattern = pattern
        self.replacement = replacement
        self.flags = flags

    def apply(self, text: str) -> str:
        return re.sub(self.pattern, self.replacement, text, flags=self.flags)


class StripCleaningRule(CleaningRule):
    """Cleaning rule that strips whitespace and specific characters."""

    def __init__(self, chars: str | None = None):
        self.chars = chars

    def apply(self, text: str) -> str:
        return text.strip(self.chars)


class ColorUtils:
    @staticmethod
    def normalize_color(color: str) -> str | None:
        """
        Normalize a color string to a standard hex format (#aabbcc, lowercase).
        Returns None if the color is invalid or empty.
        """
        return DataCleaner.normalize_color(color)


class DataCleaner:
    """Centralized, extensible data cleaning system."""

    COLOR_RULES = [
        StripCleaningRule(),
    ]

    NAME_RULES = [
        RegexCleaningRule(r"\s*background_\d+", "", re.IGNORECASE),
        RegexCleaningRule(r"\s*z-index\s*\d+.*", "", re.IGNORECASE),
        RegexCleaningRule(r"_\d+$", ""),
        RegexCleaningRule(r"\s+", " "),
        StripCleaningRule(),
    ]

    @staticmethod
    def clean_with_rules(text: str, rules: Sequence[CleaningRule]) -> str:
        """Apply a list of cleaning rules in sequence."""
        if not text:
            return ""

        result = text
        for rule in rules:
            result = rule.apply(result)
        return result

    @classmethod
    def clean_block_name(cls, name: str) -> str:
        """Clean a block name using standard rules."""
        return cls.clean_with_rules(name, cls.NAME_RULES)

    @classmethod
    def extract_index(cls, name: str, block_type: str | None = None) -> int | None:
        """Extract numeric index from name using various patterns."""
        if not name:
            return None

        paren_match = re.search(r"\(([^)]+)\)", name)
        if paren_match:
            inner = paren_match.group(1)
            idx_match = re.search(r"_(\d+)", inner)
            if idx_match:
                return int(idx_match.group(1))

        if block_type:
            pattern = rf"{block_type}[_\s-]*(\d+)"
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return int(match.group(1))

        match = re.search(r"_(\d+)$", name)
        if match:
            return int(match.group(1))

        match = re.search(r"percentage\s*(\d+)", name, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    @classmethod
    def normalize_color(cls, color: str) -> str | None:
        """Normalize a color string to standard hex format."""
        if not color or not isinstance(color, str):
            return None

        cleaned = cls.clean_with_rules(color, cls.COLOR_RULES).lower()

        if cleaned.startswith("#"):
            cleaned = cleaned.lstrip("#")
        if re.fullmatch(r"[0-9a-f]{6}", cleaned):
            return f"#{cleaned}"
        if re.fullmatch(r"[0-9a-f]{3}", cleaned):
            cleaned = "".join([c * 2 for c in cleaned])
            return f"#{cleaned}"
        return None
