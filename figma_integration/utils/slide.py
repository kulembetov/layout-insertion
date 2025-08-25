import configuration as config


class SlideUtils:
    @staticmethod
    def detect_slide_type(container_name: str, slide_number: int) -> str:
        """Detect slide type using only config.py as the source of truth."""
        key = container_name.strip().lower()
        number = config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, slide_number)
        return config.SLIDE_NUMBER_TO_TYPE.get(number, "classic")

    @staticmethod
    def get_slide_number(parent_name: str) -> int:
        """Get slide number from parent container name (case-insensitive, trimmed). Use config.py as the only source of truth."""
        key = parent_name.strip().lower()
        result = config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, None)
        if result is None:
            return 1
        return result
