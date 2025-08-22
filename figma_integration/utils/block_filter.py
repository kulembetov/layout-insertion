from collections.abc import Callable

import configuration as config
from figma_integration.filters import FilterConfig, FilterMode
from figma_integration.models import ExtractedBlock

from .checker import Checker


class BlockFilterUtils:
    @staticmethod
    def _check_mode(mode: FilterMode, filter_config: FilterConfig, get: Callable) -> bool:
        if mode == FilterMode.ALL:
            return True
        if mode == FilterMode.SLIDE_GROUP:
            slide_number = get("slide_number") or get("slideNumber")
            if slide_number is not None:
                return slide_number in getattr(filter_config, "target_slides", [])
        if mode == FilterMode.SLIDE_NAME:
            slide_name = get(config.FigmaKey.NAME)
            if slide_name is not None:
                return slide_name in getattr(filter_config, "target_names", [])
        return True

    @staticmethod
    def should_include(node_or_block: dict | ExtractedBlock, filter_config: FilterConfig) -> bool:
        """
        Centralized logic for whether a node/block should be included based on filter_config.
        Handles z-index, marker, visibility, and filter mode.
        Accepts either a Figma node (dict) or an ExtractedBlock/dict.
        """

        def get(key: str):
            if isinstance(node_or_block, dict):
                return node_or_block.get(key, None)
            return getattr(node_or_block, key, None)

        name = get(config.FigmaKey.NAME) or ""
        _marker: list[str] | None = getattr(filter_config, "target_statuses", None)
        marker: str | None = _marker[0] if _marker else None

        exclude_hidden = getattr(filter_config, "exclude_hidden", True) and get(config.FigmaKey.VISIBLE) is False
        marker_check = not Checker.check_marker(marker, name)
        z_index_requirement = getattr(filter_config, "require_z_index", True) and not Checker.check_z_index(name)
        if exclude_hidden or marker_check or z_index_requirement:
            return False

        mode = getattr(filter_config, "mode", FilterMode.ALL)
        return BlockFilterUtils._check_mode(mode, filter_config, get)
