import json
import os
import re
from typing import Any

import uuid_utils as uuid

from db_work import constants


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


def extract_frame_data(data: dict) -> list[dict]:
    """Recursive extraction from cache."""
    results = []

    def recursive_extract(obj):
        nonlocal results

        if isinstance(obj, dict):
            if all(key in obj for key in ["slide_number", "frame_name", "imagesCount", "sentences", "forGeneration", "slide_type", "dimensions"]):
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


# Выделить в класс
class SlideLayoutUtils:
    """Slide Layout Utils"""

    def __init__(self):
        self.miniatures_base_path = constants.MINIATURES_BASE_PATH
        self.slide_nimber_to_path = constants.SLIDE_NUMBER_TO_TYPE
        self.slide_number_to_number = constants.SLIDE_NUMBER_TO_NUMBER
        self.miniature_extension = constants.MINIATURE_EXTENSION

    # def build_slide_icon_url(self, slide_type: str, slide_name: str, slide_number: int) -> str:
    #     """Generate icon URL for slide layout."""

    #     skip_number_types = {self.slide_nimber_to_path.get(n) for n in [1, 5, 8, 12, -1]}
    #     miniature_folder = self._camel_to_snake(slide_type)

    #     if slide_type in skip_number_types:
    #         return f"{self.miniatures_base_path}/{miniature_folder}/{slide_name}{self.miniature_extension}"

    #     number_for_icon = self.slide_number_to_number.get(slide_number)
    #     if number_for_icon is not None:
    #         return f"{self.miniatures_base_path}/{miniature_folder}/{number_for_icon}_{slide_name}{self.miniature_extension}"

    #     return f"{self.miniatures_base_path}/{miniature_folder}/{slide_name}{self.miniature_extension}"

    def build_slide_icon_url(self, slide_type: str, slide_name: str, slide_number: int) -> str:
        """Generate icon URL for slide layout."""
        # Slide numbers that should NOT have numbers in their miniature paths
        skip_number_slides = {1, 5, 7, 8, 13, -1}
        miniature_folder = self._camel_to_snake(slide_type)

        # If this slide number should skip numbering, return without number
        if slide_number in skip_number_slides:
            return f"{self.miniatures_base_path}/{miniature_folder}/{slide_name}{self.miniature_extension}"

        # For slide numbers that should have numbers, get the number from the mapping
        number_for_icon = self.slide_number_to_number.get(slide_number)
        if number_for_icon is not None:
            return f"{self.miniatures_base_path}/{miniature_folder}/{number_for_icon}_{slide_name}{self.miniature_extension}"

        # Fallback: if no number mapping found, return without number
        return f"{self.miniatures_base_path}/{miniature_folder}/{slide_name}{self.miniature_extension}"

    def _camel_to_snake(self, name):
        """Convert camelCase or PascalCase to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
