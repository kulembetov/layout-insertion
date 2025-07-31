from typing import Callable, Optional, Any

from api_v1.constants import TYPES
from api_v1.services.data_classes import ExtractedBlock
from api_v1.services.filters.filter_settings import LegacyFilterMode, LegacyFilterConfig
from api_v1.utils.checkers import Checker


# codeblock for 'should_include', don't use/import this
def _check_mode(mode: LegacyFilterMode, filter_config: LegacyFilterConfig, get: Callable) -> bool:
    if mode == LegacyFilterMode.ALL:
        return True
    if mode == LegacyFilterMode.SPECIFIC_SLIDES:
        slide_number = get('slide_number') or get('slideNumber')
        if slide_number is not None:
            return slide_number in getattr(filter_config, 'target_slides', [])
    if mode == LegacyFilterMode.SPECIFIC_BLOCKS:
        sql_type = get('sql_type')
        if sql_type is not None:
            return sql_type in getattr(filter_config, 'target_block_types', [])
    if mode == LegacyFilterMode.BY_TYPE:
        parent_container = get('parent_container')
        if parent_container is not None:
            return parent_container in getattr(filter_config, 'target_containers', [])
    return True


def should_include(node_or_block: dict | ExtractedBlock, filter_config) -> bool:
    """
    Centralized logic for whether a node/block should be included based on filter_config.
    Handles z-index, marker, visibility, and filter mode.
    Accepts either a Figma node (dict) or an ExtractedBlock/dict.
    """
    def get(key: str) -> Optional[Any]:
        if isinstance(node_or_block, dict):
            return node_or_block.get(key, None)
        return getattr(node_or_block, key, None)

    name = get(TYPES.FK_NAME) or ''
    marker = getattr(filter_config, 'ready_to_dev_marker', None)

    exclude_hidden = getattr(filter_config, 'exclude_hidden', True) and get(TYPES.FK_VISIBLE) is False
    marker_check = not Checker.check_marker(marker, name)
    z_index_requirement = getattr(filter_config, 'require_z_index', True) and not Checker.check_z_index(name)
    if exclude_hidden or marker_check or z_index_requirement:
        return False

    # Filter mode logic
    mode = getattr(filter_config, 'mode', None)
    return _check_mode(mode, filter_config, get)
