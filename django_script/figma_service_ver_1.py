import requests
from enum import Enum
from typing import Dict, List,Optional
import json


class FilterMode(Enum):
    ALL = "all"
    SPECIFIC_SLIDES = "specific_slides"
    BY_TYPE = "by_type"


class FilterConfig:
    def __init__(
        self,
        mode: FilterMode = FilterMode.ALL,
        target_slides: Optional[List[int]] = None,
        target_container_types: Optional[List[str]] = None
    ):
        self.mode = mode
        self.target_slides = target_slides or []
        self.target_container_types = target_container_types or []


class EnhancedFigmaExtractor:
    def __init__(self, file_id: str, headers: Dict[str, str], filter_config: Optional[FilterConfig] = None):
        self.file_id = file_id
        self.headers = headers
        self.filter_config = filter_config or FilterConfig()

    def fetch(self) -> List[Dict]:
        response = requests.get(
            f'https://api.figma.com/v1/files/{self.file_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return  response.json()['document']['children']

    def recursive_slide_traversal_and_filter(self, data):
        if self.filter_config.mode == FilterMode.ALL:
            return data
        else:
            results = []
            for node in data:
                if node.get('type') == 'CANVAS':
                    for child in node.get('children', []):
                        if self.filter_config.mode == FilterMode.SPECIFIC_SLIDES and \
                            child.get('name') in self.filter_config.target_slides:
                            results.append(child)
                        elif self.filter_config.mode == FilterMode.BY_TYPE and \
                            child.get('type') in self.filter_config.target_container_types:
                            results.append(child)

                self.recursive_slide_traversal_and_filter(node.get('children', []))
            return results

    def extract(self):
        data = self.fetch()
        result = self.recursive_slide_traversal_and_filter(data)
        with open("output.json", "w", encoding="utf-8") as outfile:
            json.dump(result, outfile, ensure_ascii=False, indent=4)
        return result
