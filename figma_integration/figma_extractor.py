from dataclasses import asdict
from typing import Any, cast

import requests

import configuration as config
from log_utils import logs, setup_logger
from redis_cache.utils import get_cached_request, set_cached_request

from .base import FigmaSession
from .filters import FilterMode
from .models import ExtractedBlock, ExtractedSlide
from .utils.block import BlockUtils
from .utils.block_filter import BlockFilterUtils
from .utils.block_type import BlockTypeUtils
from .utils.check import CheckUtils
from .utils.extractor import extractor
from .utils.slide import SlideUtils
from .utils.slide_builder import slide_builder

logger = setup_logger(__name__)


@logs(logger, on=False)
class FigmaExtractor:
    def __init__(self, session: FigmaSession):
        self.session = session

    @logs(logger, on=True)
    def fetch_comments(self) -> dict[str, str]:
        """Fetch all comments from Figma API in a single call and return a mapping of node_id to comment."""
        comments_map = {}
        try:
            logger.info("Fetching comments from Figma API...")
            response = requests.get(
                f"https://api.figma.com/v1/files/{self.session.file_id}/comments",
                headers=self.session.headers,
                timeout=30,
            )
            response.raise_for_status()
            comments_data = response.json()

            logger.info(f"Comments API response keys: {list(comments_data.keys())}")

            if "comments" in comments_data:
                logger.info(f"Total comments in response: {len(comments_data['comments'])}")
                for i, comment in enumerate(comments_data["comments"][:3]):
                    logger.info(f"Comment {i+1}: {comment}")
            else:
                logger.info(f"No 'comments' key found in response. Available keys: {list(comments_data.keys())}")

            for comment in comments_data.get("comments", []):
                client_meta = comment.get("client_meta", {})
                node_id = client_meta.get("node_id")
                message = comment.get("message", "")
                if node_id and message and node_id not in comments_map:
                    comments_map[node_id] = message
                    logger.info(f"Mapped comment for node {node_id}: {message[:50]}...")

            logger.info(f"Successfully mapped {len(comments_map)} comments")
            return comments_map

        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to fetch comments: {e}")
            return {}
        except Exception as e:
            logger.debug(f"Error fetching comments: {e}")
            return {}

    def fetch(self) -> list[dict]:
        """
        Returns JSON response from Figma by 'file_id'.
        """
        figma_response = requests.get(f"https://api.figma.com/v1/files/{self.session.file_id}", headers=self.session.headers, timeout=180)
        figma_response.raise_for_status()

        data = figma_response.json()
        response = BlockUtils.get_node_property(data["document"], config.FigmaKey.CHILDREN, [])

        set_cached_request(self.session.file_id, response)
        return response

    # =========== Extract codeblocks ==============
    @logs(logger, on=True)
    def _get_slides(self, comments: dict[str, str]) -> list[ExtractedSlide]:
        data = get_cached_request(self.session.file_id)

        if data is None:
            pages = self.fetch()
        else:
            pages = data

        all_slides: list[ExtractedSlide] = []
        for page in pages:
            logger.info(f"\nProcessing page: {BlockUtils.get_node_property(page, config.FigmaKey.NAME, 'Unnamed')}")
            page_slides = self._traverse_and_extract(page, "", comments)
            all_slides.extend(page_slides)

        return all_slides

    @staticmethod
    def _get_summary(slides: list[ExtractedSlide]) -> dict[str, int | dict[str | int, Any]]:
        summary: dict[str, int | dict[Any, Any]] = {"total_slides": len(slides), "total_blocks": sum(len(slide.blocks) for slide in slides), "slide_types": {}, "block_types": {}, "slide_distribution": {}}

        for slide in slides:
            slide_type = slide.slide_type

            slide_types = cast(dict[Any, Any], summary["slide_types"])
            slide_types[slide_type] = slide_types.get(slide_type, 0) + 1
            summary["slide_types"] = slide_types

            slide_distribution = cast(dict[Any, Any], summary["slide_distribution"])
            slide_distribution[slide.number] = slide.container_name
            summary["slide_distribution"] = slide_distribution

            for block in slide.blocks:
                block_type = block.sql_type
                block_types = cast(dict[Any, Any], summary["block_types"])
                block_types[block_type] = block_types.get(block_type, 0) + 1
                summary["block_types"] = block_types

        return summary

    def extract_data(self) -> dict[str, str | dict | list | int]:
        """Main extraction method. Returns extracted slides and metadata, or error info on failure."""
        try:
            comments = self.fetch_comments()
            all_slides = self._get_slides(comments)
            summary = self._get_summary(all_slides)

            return {
                "metadata": {
                    "file_id": self.session.file_id,
                    "figma_config": asdict(config.FIGMA_CONFIG),
                    "extraction_summary": summary,
                    "filter_config": {"mode": self.session.filter_config.mode.value, "target_slides": self.session.filter_config.target_slides, "target_names": self.session.filter_config.target_names, "target_statuses": self.session.filter_config.target_statuses},
                    "sql_generator_compatibility": {
                        "valid_block_types": config.BLOCK_TYPES["block_layout_type_options"],
                        "valid_font_weights": config.VALID_FONT_WEIGHTS,
                        "slide_layout_types": config.SLIDE_LAYOUT_TYPES,
                    },
                },
                "slides": [slide_builder.slide_to_dict(slide) for slide in all_slides],
            }

        except requests.exceptions.RequestException as e:
            logger.debug(f"Request error: {e}")
            return {"metadata": {"file_id": self.session.file_id, "error": f"Request error: {e}"}, "slides": []}

        except Exception as e:
            logger.debug(f"Unexpected error: {e}")
            return {
                "metadata": {
                    "file_id": self.session.file_id,
                    "error": f"Unexpected error: {e}",
                },
                "slides": [],
            }

    def _traverse_and_extract(
        self,
        node: dict[str, str | int | float | bool | dict | list],
        parent_name: str = "",
        comments_map: dict[str, str] | None = None,
    ) -> list[ExtractedSlide]:
        """Traversal with filtering"""
        slides: list[ExtractedSlide] = []

        if self._is_target_frame(node):
            logger.info(f"Found target frame: \"{node['name']}\"")
            logger.info(f'Parent container: "{parent_name}"')

            abs_box_raw = node.get("absoluteBoundingBox")
            if isinstance(abs_box_raw, dict):
                x_raw = abs_box_raw.get("x")
                y_raw = abs_box_raw.get("y")
                if isinstance(x_raw, (int, float)) and isinstance(y_raw, (int, float)):
                    frame_origin = {
                        "x": int(x_raw),
                        "y": int(y_raw),
                    }
                else:
                    frame_origin = {"x": 0, "y": 0}
            else:
                frame_origin = {"x": 0, "y": 0}

            slide_number = SlideUtils.get_slide_number(parent_name)

            if self.session.filter_config.mode == FilterMode.SLIDE_GROUP and slide_number not in self.session.filter_config.target_slides:
                return slides

            slide_type = SlideUtils.detect_slide_type(parent_name, slide_number)

            target_width_raw = config.FIGMA_CONFIG.TARGET_WIDTH
            target_height_raw = config.FIGMA_CONFIG.TARGET_HEIGHT
            if isinstance(target_width_raw, (int, float)) and isinstance(target_height_raw, (int, float)):
                dimensions = {
                    "w": int(target_width_raw),
                    "h": int(target_height_raw),
                }
            else:
                dimensions = {"w": 1200, "h": 675}

            blocks = self._collect_blocks(node, frame_origin, slide_number, parent_name, comments_map)

            if blocks or self.session.filter_config.mode == FilterMode.ALL:
                slide = ExtractedSlide(
                    number=slide_number,
                    container_name=parent_name,
                    frame_name=str(node["name"]),
                    slide_type=slide_type,
                    blocks=blocks,
                    frame_id=str(node["id"]),
                    dimensions=dimensions,
                )
                slide._figma_node = node
                slides.append(slide)
                logger.info(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")

            return slides

        children_raw = node.get("children")
        if isinstance(children_raw, list):
            for child in children_raw:
                if isinstance(child, dict):
                    name_raw = node.get("name", "")
                    parent_name_str = str(name_raw) if name_raw is not None else ""
                    child_slides = self._traverse_and_extract(child, parent_name_str, comments_map)
                    slides.extend(child_slides)

        return slides

    def _is_target_frame(self, node: dict[str, str | int | float | bool | dict | list]) -> bool:
        """Check if node is a target frame, now supports 'ready to dev' marker"""
        if not BlockUtils.get_node_property(node, "absoluteBoundingBox"):
            return False

        marker = getattr(self.session.filter_config, "ready_to_dev_marker", None)
        if marker:
            name = BlockUtils.get_node_property(node, "name", "").lower()
            if marker.lower() not in name:
                return False

        if self.session.filter_config.require_z_index and not CheckUtils.check_z_index(BlockUtils.get_node_property(node, "name", "")):
            return False

        abs_box = BlockUtils.get_node_property(node, "absoluteBoundingBox")
        width_match = abs(abs_box["width"] - config.FIGMA_CONFIG.TARGET_WIDTH) < 1
        height_match = abs(abs_box["height"] - config.FIGMA_CONFIG.TARGET_HEIGHT) < 1
        if not (width_match and height_match):
            return False

        area = abs_box["width"] * abs_box["height"]
        if area < self.session.filter_config.min_area:
            return False
        return True

    def _collect_blocks(
        self,
        node: dict[str, str | int | float | bool | dict | list],
        frame_origin: dict[str, int],
        slide_number: int,
        parent_container: str,
        comments_map: dict[str, str] | None = None,
    ) -> list[ExtractedBlock]:
        """Recursively collect blocks from a Figma node, filtering and normalizing as needed."""
        blocks: list[ExtractedBlock] = []

        if not BlockUtils.get_node_property(node, "absoluteBoundingBox"):
            return blocks
        if not BlockFilterUtils.should_include(node, self.session.filter_config):
            return blocks

        name = BlockUtils.get_node_property(node, "name", "")
        has_z = CheckUtils.check_z_index(name)

        if has_z:
            figma_type, sql_type = BlockTypeUtils.detect_block_type(node)
            abs_box = BlockUtils.get_node_property(node, "absoluteBoundingBox")
            rotation = extractor.extract_rotation(node)

            dimensions = {
                "x": round(abs_box["x"] - frame_origin["x"]),
                "y": round(abs_box["y"] - frame_origin["y"]),
                "w": round(abs_box["width"]),
                "h": round(abs_box["height"]),
                "rotation": rotation,
            }

            if BlockFilterUtils.should_skip_full_image_block(sql_type, dimensions, name):
                logger.debug(f"Skipping {sql_type} block {name} (full image {config.FIGMA_CONFIG.TARGET_WIDTH}x{config.FIGMA_CONFIG.TARGET_HEIGHT})")
            else:
                styles = extractor.extract_block_styles(node, sql_type, name)
                text_content = extractor.extract_text_content(node, sql_type)

                block = BlockUtils.create_extracted_block(node, figma_type, sql_type, name, dimensions, styles, slide_number, parent_container, text_content, comments_map)

                if BlockFilterUtils.should_include(block, self.session.filter_config):
                    blocks.append(block)
                    logger.info(f"Added {sql_type} block: {name}")

                    blur_value = styles.get("blur", 0)
                    blur_info = f" | Blur: {blur_value}px" if isinstance(blur_value, (int, float)) and blur_value > 0 else ""
                    # line_height_info = f" | LineHeight: {styles.get('lineHeight', 'N/A')}" if styles.get("lineHeight") else ""
                    logger.debug(f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{blur_info}")

        if BlockUtils.get_node_property(node, "children") and not (getattr(self.session.filter_config, "exclude_hidden", True) and BlockUtils.get_node_property(node, "visible") is False):
            for node_child in BlockUtils.get_node_property(node, "children"):
                blocks.extend(self._collect_blocks(node_child, frame_origin, slide_number, parent_container, comments_map))

        return blocks
