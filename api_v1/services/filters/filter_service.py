from typing import Any, Optional, Dict

from .filter_settings import LegacyFilterMode, LegacyFilterConfig
from api_v1.services.figma_api import FigmaAPI


class FilterFigmaApi(FigmaAPI):
    """Use different types of filtration."""

    def __init__(self, file_id: str, token: Optional[str] = None, filter_params: Optional[list] = None) -> None:
        super().__init__(file_id=file_id, token=token)
        self.filter_params = filter_params

    def extract_specific_slides(self) -> Dict[str, Any]:
        """Extract specific slides from Figma."""

        self.filter_config = LegacyFilterConfig(
            mode=LegacyFilterMode.SPECIFIC_SLIDES,
            target_slides=self.filter_params,
            require_z_index=True
        )
        return self.extract()
    

    def extract_specific_blocks(self) -> Dict[str, Any]:
        """Extract slides containing specific block types."""

        self.filter_config = LegacyFilterConfig(
            mode=LegacyFilterMode.SPECIFIC_BLOCKS,
            target_block_types=self.filter_params,
        )
        return self.extract()
    
    def extract_by_type(self) -> Dict[str, Any]:
        """Extract slides from specific containers"""

        self.filter_config = LegacyFilterConfig(
            mode=LegacyFilterMode.BY_TYPE,
            target_containers=self.filter_params
        )
        return self.extract()
    
    def extract_ready_to_dev(self) -> Dict[str, Any]:
        """Extract blocks marked as ready for development."""
        self.filter_config = LegacyFilterConfig(mode=LegacyFilterMode.READY_TO_DEV)
        return self.extract()
