import json
import os
from typing import Any

import configuration as config
from log_utils import logs, setup_logger

logger = setup_logger(__name__)


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

    @staticmethod
    @logs(logger, on=False)
    def save_results(data: dict[str, str | dict | list | int], output_file: str | None = None) -> str:
        """Save extracted data to file"""
        if not data:
            return ""
        output_dir_raw = config.FIGMA_CONFIG.OUTPUT_DIR
        if not isinstance(output_dir_raw, str):
            output_dir_raw = str(output_dir_raw)
        if not os.path.exists(output_dir_raw):
            os.makedirs(output_dir_raw)

        if not output_file:
            output_file_raw = config.FIGMA_CONFIG.OUTPUT_FILE
            if not isinstance(output_file_raw, str):
                output_file_raw = str(output_file_raw)
            output_file = f"{output_dir_raw}/{output_file_raw}_config_compatible.json"

        HelpUtils.json_dump(data, output_file)

        logger.info(f"\nData saved: {output_file}")

        if isinstance(data, dict):
            metadata = data.get("metadata", {})
            if isinstance(metadata, dict):
                summary = metadata.get("extraction_summary", {})
                if isinstance(summary, dict):
                    logger.info("\nEXTRACTION SUMMARY:")
                    logger.info(f"   Total slides: {summary.get('total_slides', 0)}")
                    logger.info(f"   Total blocks: {summary.get('total_blocks', 0)}")
                    logger.info(f"   Slide types: {summary.get('slide_types', {})}")
                    logger.info(f"   Block types: {summary.get('block_types', {})}")
                    logger.info(f"   Distribution: {summary.get('slide_distribution', {})}")

        return output_file
