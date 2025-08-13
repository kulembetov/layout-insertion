import re


class FontUtils:
    @staticmethod
    def normalize_font_family(font_family: str) -> str:
        if not font_family:
            return ""
        return re.sub(
            r"[^a-z0-9_]",
            "",
            font_family.strip().lower().replace(" ", "_").replace("-", "_"),
        )
