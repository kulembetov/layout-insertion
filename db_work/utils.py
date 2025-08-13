import json
import os
from typing import Any

import uuid_utils as uuid


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
                result_dict = {"number": obj.get("slide_number"), "name": obj.get("frame_name").split()[0], "imagesCount": obj.get("imagesCount"), "sentences": obj.get("sentences"), "forGeneration": obj.get("forGeneration"), "isLast": obj.get("slide_type"), "dimensions": obj.get("dimensions"), "blocks": obj.get("blocks")}
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
