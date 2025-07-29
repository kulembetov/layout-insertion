from typing import Optional

from api_v1.constants import CONSTANTS


class Checker:
    @staticmethod
    def check_z_index(name: str) -> bool:
        """Checks if the frame name contains a Z-index. """
        return 'z-index' in name

    @staticmethod
    def check_dimensions(absolute_bounding_box: dict) -> bool:
        """Checks whether the frame size matches the target width and height."""
        width_diff = abs(absolute_bounding_box['width'] - CONSTANTS.FIGMA_CONFIG['TARGET_WIDTH'])
        height_diff = abs(absolute_bounding_box['height'] - CONSTANTS.FIGMA_CONFIG['TARGET_HEIGHT'])
        return width_diff < 1 and height_diff < 1

    @staticmethod
    def check_min_area(absolute_bounding_box: dict, min_area: int) -> bool:
        """Checks whether the frame area exceeds the minimum threshold."""
        area = absolute_bounding_box['width'] * absolute_bounding_box['height']
        return area >= min_area

    @staticmethod
    def check_marker(ready_to_dev_marker: Optional[str], name: str) -> bool:
        """Checks for the 'ready to dev' label."""
        if ready_to_dev_marker:
            return ready_to_dev_marker.lower() in name.lower()
        return True
