from typing import Any

import requests

from django_app.api_v1.constants import BLOCKS, CONSTANTS, SLIDES, TYPES
from django_app.api_v1.redis.utils import get_cached_request, set_cached_request
from django_app.api_v1.utils.builders import slide_to_dict
from django_app.api_v1.utils.checkers import Checker
from django_app.api_v1.utils.detectors import detect_block_type, detect_slide_type
from django_app.api_v1.utils.extractors import Extractor
from django_app.api_v1.utils.filters import should_include
from django_app.api_v1.utils.helpers import get_slide_number, round5
from log_utils import logs, setup_logger
from .data_classes import ExtractedBlock, ExtractedSlide
from .filters.filter_settings import FilterConfig, FilterMode

logger = setup_logger(__name__)


@logs(logger, on=True)
class FigmaAPI:
    def __init__(self, *, file_id: str | None = None, token: str | None = None, filter_config: FilterConfig | None = None) -> None:
        self._file_id: str = file_id or "-"
        self._token: str = token or "-"
        self._filter_config: FilterConfig = filter_config or FilterConfig()

    @property
    def file_id(self) -> str:
        return self._file_id

    @file_id.setter
    def file_id(self, file_id: str) -> None:
        if isinstance(file_id, str):
            self._file_id = file_id
        else:
            raise TypeError("'file_id' must be str.")

    @property
    def token(self) -> str:
        return self._token

    @token.setter
    def token(self, token: str) -> None:
        if isinstance(token, str):
            self._token = token
        else:
            raise TypeError("'token' must be str.")

    @property
    def filter_config(self) -> FilterConfig:
        return self._filter_config

    @filter_config.setter
    def filter_config(self, config: FilterConfig) -> None:
        if isinstance(config, FilterConfig):
            self._filter_config = config
        else:
            raise TypeError("'config' must be FilterConfig.")

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Figma-Token": self._token}

    def fetch(self) -> list[dict]:
        """
        Returns JSON response from Figma by 'file_id'.
        """

        figma_response = requests.get(f"https://api.figma.com/v1/files/{self.file_id}", headers=self.headers, timeout=180)
        figma_response.raise_for_status()
        response: list[dict] = figma_response.json()["document"][TYPES.FK_CHILDREN]
        set_cached_request(self.file_id, response)

        return response

    @logs(logger, on=True)
    def fetch_comments(self) -> dict:
        """Fetch comments from the Figma API and map them by node_id with full metadata."""
        try:
            response = requests.get(f"https://api.figma.com/v1/files/{self.file_id}/comments", headers=self.headers, timeout=180)
            response.raise_for_status()
            comments_data = response.json().get("comments", [])
            node_comments: dict[str, list[str]] = {}

            for comment in comments_data:
                client_meta = comment.get("client_meta")
                comment_message: str = comment.get("message", "")

                if isinstance(client_meta, list):
                    for meta in client_meta:
                        node_id = meta.get("node_id")
                        if node_id:
                            node_comments.setdefault(node_id, []).append(comment_message)
                elif isinstance(client_meta, dict):
                    node_id = client_meta.get("node_id")
                    if node_id:
                        node_comments.setdefault(node_id, []).append(comment_message)

            logger.info(f"Fetched {len(comments_data)} comments for {len(node_comments)} nodes")
            if node_comments:
                logger.info(f"Comment distribution: {list(node_comments.keys())[:5]}...")  # Show first 5 node IDs
            return node_comments

        except Exception as e:
            logger.debug(f"Failed to fetch comments: {e}")
            return {}

    # =========== Extract codeblocks ==============
    @logs(logger, on=True)
    def _get_slides(self) -> list[ExtractedSlide]:
        data = get_cached_request(self.file_id)

        if data:
            pages = data
        else:
            pages = self.fetch()

        from django_app.api_v1.utils.helpers import json_dump
        json_dump(data, 'testbag')

        all_slides: list[ExtractedSlide] = []
        for page in pages:
            logger.info(f"\nProcessing page: {page.get(TYPES.FK_NAME, 'Unnamed')}")
            page_slides = self.traverse_and_extract(page)
            all_slides.extend(page_slides)

        return all_slides

    @staticmethod
    def _get_summary(slides: list[ExtractedSlide]) -> dict[str, int | dict[str | int, Any]]:
        # Generate summary
        summary: dict[str, int | dict] = {"total_slides": len(slides), "total_blocks": sum(len(slide.blocks) for slide in slides), "slide_types": {}, "block_types": {}, "slide_distribution": {}}

        for slide in slides:
            slide_type = slide.slide_type
            summary["slide_types"][slide_type] = summary["slide_types"].get(slide_type, 0) + 1
            summary["slide_distribution"][slide.number] = slide.container_name

            for block in slide.blocks:
                block_type = block.sql_type
                summary["block_types"][block_type] = summary["block_types"].get(block_type, 0) + 1

        return summary

    def extract(self) -> dict[str, Any]:
        try:
            all_slides = self._get_slides()
            summary = self._get_summary(all_slides)
            comments = self.fetch_comments()

            return {
                "metadata": {
                    "file_id": self.file_id,
                    "figma_config": CONSTANTS.FIGMA_CONFIG,
                    "extraction_summary": summary,
                    "filter_config": {"mode": self.filter_config.mode.value, "target_slides": self.filter_config.target_slides, "target_names": self.filter_config.target_names, "target_statuses": self.filter_config.target_statuses},
                    "sql_generator_compatibility": {"valid_block_types": BLOCKS.BLOCK_TYPES["block_layout_type_options"], "valid_font_weights": CONSTANTS.VALID_FONT_WEIGHTS, "slide_layout_types": SLIDES.SLIDE_LAYOUT_TYPES},
                },
                "slides": [slide_to_dict(slide, comments) for slide in all_slides],
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {"metadata": {"file_id": self.file_id, "error": str(e)}, "slides": []}

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"metadata": {"file_id": self.file_id, "error": str(e)}, "slides": []}

    # =============================================
    @logs(logger, on=True)
    def traverse_and_extract(self, node: dict[str, Any], parent_name: str = "") -> list[ExtractedSlide]:
        """Enhanced traversal with filtering"""
        slides: list[ExtractedSlide] = []

        if self.is_target_frame(node):
            logger.info(f'Found target frame: "{node[TYPES.FK_NAME]}"')
            logger.info(f'Parent container: "{parent_name}"')

            frame_origin = {"x": node[TYPES.FK_ABS_BOX]["x"], "y": node[TYPES.FK_ABS_BOX]["y"]}

            slide_number = get_slide_number(parent_name)
            slide_type = detect_slide_type(parent_name, slide_number)

            # Skip if not in target slides (when filtering by specific slides)
            if self.filter_config.mode == FilterMode.SLIDE_GROUP and slide_number not in self.filter_config.target_slides:
                return slides

            blocks = self.collect_blocks(node, frame_origin, slide_number, parent_name)

            if blocks or self.filter_config.mode == FilterMode.ALL:
                slide = ExtractedSlide(number=slide_number, container_name=parent_name, frame_name=node[TYPES.FK_NAME], slide_type=slide_type, blocks=blocks, frame_id=node["id"], dimensions={"w": CONSTANTS.FIGMA_CONFIG["TARGET_WIDTH"], "h": CONSTANTS.FIGMA_CONFIG["TARGET_HEIGHT"]})
                # Attach the original node for color extraction
                slide._figma_node = node
                slides.append(slide)
                logger.info(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")

            return slides

        # Continue traversing children
        if node.get(TYPES.FK_CHILDREN):
            for child in node[TYPES.FK_CHILDREN]:
                child_slides = self.traverse_and_extract(child, node[TYPES.FK_NAME])
                slides.extend(child_slides)

        return slides

    def is_target_frame(self, node: dict[str, Any]) -> bool:
        """Check if node is a target frame, now supports 'ready to dev' marker."""

        if not node.get(TYPES.FK_ABS_BOX):
            return False

        if self.filter_config.require_z_index and not Checker.check_z_index(node.get(TYPES.FK_NAME, "")):
            return False

        if self.filter_config.mode == FilterMode.STATUS:
            dev_status = node.get("devStatus", {}).get("type")
            if dev_status != "READY_FOR_DEV":
                return False

        if not Checker.check_dimensions(node[TYPES.FK_ABS_BOX]):
            return False

        if not Checker.check_min_area(node[TYPES.FK_ABS_BOX], self.filter_config.min_area):
            return False

        return True

    
    def collect_blocks(
        self,
        node: dict[str, str | int | float | bool | dict | list],
        frame_origin: dict[str, int],
        slide_number: int,
        parent_container: str,
        comments_map: dict[str, str] | None = None,
    ) -> list[ExtractedBlock]:
        """Recursively collect blocks from a Figma node, filtering and normalizing as needed."""
        blocks: list[ExtractedBlock] = []
        if not Extractor.get_node_property(node, "absoluteBoundingBox"):
            return blocks
        if not should_include(node, self.filter_config):
            return blocks
        name = Extractor.get_node_property(node, "name", "")
        has_z = Checker.check_z_index(name)
        if has_z:
            figma_type, sql_type = detect_block_type(node)
            abs_box = Extractor.get_node_property(node, "absoluteBoundingBox")
            left = abs_box["x"] - frame_origin["x"]
            top = abs_box["y"] - frame_origin["y"]
            # Extract rotation
            rotation = Extractor.extract_rotation(node)

            dimensions = {
                "x": round(left),
                "y": round(top),
                "w": round(abs_box["width"]),
                "h": round(abs_box["height"]),
                "rotation": rotation,
            }
            name_lower = name.lower()
            is_precompiled = "precompiled" in name_lower
            should_skip = sql_type == "image" and dimensions["x"] == 0 and dimensions["y"] == 0 and dimensions["w"] == CONSTANTS.FIGMA_CONFIG["TARGET_WIDTH"] and dimensions["h"] == CONSTANTS.FIGMA_CONFIG["TARGET_HEIGHT"] and not is_precompiled
            if should_skip:
                # logger.log_block_event(
                #     f"Skipping {sql_type} block {name} (full image {CONSTANTS.FIGMA_CONFIG['TARGET_WIDTH']}x{CONSTANTS.FIGMA_CONFIG['TARGET_HEIGHT']})",
                #     level="debug",
                # )
                ...
            else:
                base_styles = Extractor.extract_text_styles(node, sql_type)
                styles: dict[str, str | int | float | bool | list] = {}
                for key, value in base_styles.items():
                    if isinstance(value, (str, int, float, bool, list)):
                        styles[key] = value
                    else:
                        styles[key] = str(value)  # Convert to string as fallback
                z_index = Extractor.extract_z_index(name)
                if z_index == 0:
                    z_index = CONSTANTS.Z_INDEX_DEFAULTS.get(sql_type, CONSTANTS.Z_INDEX_DEFAULTS["default"])
                styles["zIndex"] = z_index

                # Extract border radius and add to styles (always include, even if 0)
                has_border_radius, border_radius = Extractor.extract_border_radius_from_node(node)
                styles["borderRadius"] = border_radius

                opacity = Extractor.extract_opacity(node)
                styles["opacity"] = opacity

                # Extract blur for non-text blocks (text blocks already have blur from extract_text_styles)
                if sql_type not in [
                    "text",
                    "blockTitle",
                    "slideTitle",
                    "subTitle",
                    "number",
                    "email",
                    "date",
                    "name",
                    "percentage",
                ]:
                    styles["blur"] = Extractor.extract_blur(node)

                text_content = None
                if sql_type in [
                    "text",
                    "blockTitle",
                    "slideTitle",
                    "subTitle",
                    "number",
                    "email",
                    "date",
                    "name",
                    "percentage",
                ] and Extractor.is_node_type(node, "TEXT"):
                    text_content = Extractor.get_node_property(node, "characters", None)

                # Get comment from the pre-fetched comments map
                comments = comments_map.get(str(node["id"]), "") if comments_map else ""

                block = ExtractedBlock(
                    id=str(node["id"]),
                    figma_type=figma_type,
                    sql_type=sql_type,
                    name=name,
                    dimensions=dimensions,
                    styles=styles,
                    slide_number=slide_number,
                    parent_container=parent_container,
                    is_target=True,
                    text_content=text_content,
                    comments=comments,
                )
                if should_include(block, self.filter_config):
                    blocks.append(block)
                    # logger.log_block_event(f"Added {sql_type} block: {name}")
                    blur_value = styles.get("blur", 0)
                    blur_info = f" | Blur: {blur_value}px" if isinstance(blur_value, (int, float)) and blur_value > 0 else ""
                    # logger.log_block_event(
                    #     f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{blur_info}",
                    #     level="debug",
                    # )
        if Extractor.get_node_property(node, "children") and not (getattr(self.filter_config, "exclude_hidden", True) and Extractor.get_node_property(node, "visible") is False):
            for node_child in Extractor.get_node_property(node, "children"):
                blocks.extend(
                    self.collect_blocks(
                        node_child,
                        frame_origin,
                        slide_number,
                        parent_container,
                        comments_map,
                    )
                )
        return blocks
