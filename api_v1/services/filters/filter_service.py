from typing import Any, Optional, Dict

from .filter_settings import FilterMode, FilterConfig
from ..figma_api import FigmaAPI


class FilterFigmaApi:
    """Use different types of filtration."""

    def __init__(self, file_id: str, token: Optional[str] = None, filter_params: list = None) -> None:
        self.token = token
        self.filter_params = filter_params
        self.file_id = file_id

    def extract_specific_slides(self) -> Dict[str, Any]:
        """Extract specific slides from Figma."""

        filter_config = FilterConfig(
            mode=FilterMode.SPECIFIC_SLIDES,
            target_slides=self.filter_params,
            require_z_index=True
        )
        return self.get_figma_api_instance(filter_config=filter_config).extract()
    

    def extract_specific_blocks(self) -> Dict[str, Any]:
        """Extract slides containing specific block types."""

        filter_config = FilterConfig(
            mode=FilterMode.SPECIFIC_BLOCKS,
            target_block_types=self.filter_params,
        )
        return self.get_figma_api_instance(filter_config=filter_config).extract()
    
    def extract_by_type(self) -> Dict[str, Any]:
        """Extract slides from specific containers"""

        filter_config = FilterConfig(
            mode=FilterMode.BY_TYPE,
            target_containers=self.filter_params
        )
        return self.get_figma_api_instance(filter_config=filter_config).extract()
    
    def get_figma_api_instance(self, filter_config) -> 'FigmaAPI':
        """Get FigmaAPI instance."""
        figma = FigmaAPI(token=self.token)
        figma.file_id = self.file_id
        figma.filter_config = filter_config
        return figma