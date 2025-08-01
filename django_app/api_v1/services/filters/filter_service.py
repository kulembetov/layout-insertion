from typing import Any, Optional, Dict

from .filter_settings import FilterMode, FilterConfig
from django_app.api_v1.services.figma_api import FigmaAPI


class FilterFigmaApi(FigmaAPI):
    """Use different types of filtration."""

    def __init__(self, file_id: Optional[str] = None, token: Optional[str] = None, filter_names: Optional[list] = None) -> None:
        super().__init__(file_id=file_id, token=token)
        self.filter_names = filter_names

    def extract_slide_group(self) -> Dict[str, Any]:
        """Extract specific slides from Figma."""

        self.filter_config = FilterConfig(
            mode=FilterMode.SLIDE_GROUP,
            target_slides=self.filter_names,
            require_z_index=True
        )
        return self.extract()
    
    def extract_slide_name(self) -> Dict[str, Any]:
        """Extract slides from specific containers"""

        self.filter_config = FilterConfig(
            mode=FilterMode.SLIDE_NAME,
            target_names=self.filter_names
        )
        return self.extract()
    
    def extract_status(self) -> Dict[str, Any]:
        """Extract blocks marked as ready for development."""
        self.filter_config = FilterConfig(mode=FilterMode.STATUS)
        return self.extract()
