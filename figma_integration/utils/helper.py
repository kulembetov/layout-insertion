import json
import os
from typing import Any


class HelpUtils:
    @staticmethod
    def json_dump(obj, filename: str):
        with open(filename, "w", encoding="utf-8") as outfile:
            json.dump(obj, outfile, ensure_ascii=False, indent=4)

    @staticmethod
    def safe_in(item: Any, container) -> bool:
        if not container:
            return False
        return item in container

    @staticmethod
    def create_directory_structure(base_dir: str, sub_dirs: list[str]) -> None:
        """Create directory structure with subdirectories"""
        for subdir in sub_dirs:
            full_path = os.path.join(base_dir, subdir)
            os.makedirs(full_path, exist_ok=True)
            print(f"Created directory: {full_path}")
