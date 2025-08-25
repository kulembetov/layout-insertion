import configuration as config


class ValidateUtils:
    """Utility class for data validation"""

    @staticmethod
    def validate_slide_data(slide_data: dict) -> bool:
        """Validate slide data structure"""
        required_fields = ["slide_number", "frame_name", "slide_type", "blocks"]
        return all(field in slide_data for field in required_fields)

    @staticmethod
    def validate_block_data(block_data: dict) -> bool:
        """Validate block data structure"""
        required_fields = ["id", "sql_type", "name", "dimensions", "styles"]
        return all(field in block_data for field in required_fields)

    @staticmethod
    def validate_font_weight(weight: int) -> bool:
        """Validate font weight against allowed values"""
        return weight in config.VALID_FONT_WEIGHTS

    @staticmethod
    def validate_block_type(block_type: str) -> bool:
        """Validate block type against allowed values"""
        return block_type in config.BLOCK_TYPES["block_layout_type_options"]
