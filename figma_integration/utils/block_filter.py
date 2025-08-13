from figma_integration.filters import FilterConfig, FilterMode
from figma_integration.models import ExtractedBlock


class BlockFilterUtils:
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

        if getattr(filter_config, "exclude_hidden", True) and get("visible") is False:
            return False
        marker = getattr(filter_config, "ready_to_dev_marker", None)
        if marker:
            name = get("name") or ""
            if marker.lower() not in name.lower():
                return False
        if getattr(filter_config, "require_z_index", True):
            name = get("name") or ""
            if "z-index" not in name:
                return False
        mode = getattr(filter_config, "mode", None)
        if mode == FilterMode.ALL:
            return True
        if mode == FilterMode.SLIDE_GROUP:
            slide_number = get("slide_number") or get("slideNumber")
            if slide_number is not None:
                return slide_number in getattr(filter_config, "target_slides", [])
        if mode == FilterMode.SLIDE_NAME:
            slide_name = get("name")
            if slide_name is not None:
                return slide_name in getattr(filter_config, "target_names", [])
        return True
