from typing import Any

from django_app.api_v1.services.figma_api import FigmaAPI

from .filter_settings import FilterConfig, FilterMode


class FilterFigmaApi(FigmaAPI):
    """Use different types of filtration."""

    def __init__(self, *, file_id: str | None = None, token: str | None = None, filter_names: list[int | str] | None = None) -> None:
        super().__init__(file_id=file_id, token=token)
        self.filter_names: list[int | str] = filter_names or []

    def extract_slide_group(self) -> dict[str, Any]:
        """Extract specific slides from Figma."""
        target_slides: list[int] = [x for x in self.filter_names if isinstance(x, int)]
        self.filter_config = FilterConfig(mode=FilterMode.SLIDE_GROUP, target_slides=target_slides, require_z_index=True)
        return self.extract()

    def extract_slide_name(self) -> dict[str, Any]:
        """Extract slides from specific containers"""
        target_names: list[str] = [x for x in self.filter_names if isinstance(x, str)]
        self.filter_config = FilterConfig(mode=FilterMode.SLIDE_NAME, target_names=target_names)
        return self.extract()

    def extract_status(self) -> dict[str, Any]:
        """Extract blocks marked as ready for development."""
        self.filter_config = FilterConfig(mode=FilterMode.STATUS)
        return self.extract()
