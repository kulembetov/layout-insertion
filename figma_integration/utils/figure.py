import re


class FigureUtils:
    @staticmethod
    def extract_base_figure_name(name: str) -> str:
        """Extract the base figure name from a block name (e.g., 'figure (logoRfs_0)' -> 'logoRfs')."""
        if not name:
            return ""
        name_match = re.search(r"\(([^)]+)\)", name)
        if name_match:
            base_name = name_match.group(1)
            base_name = re.sub(r"_(\d+)$", "", base_name)
            return base_name
        return name

    @staticmethod
    def extract_figure_index(name: str) -> str:
        """Extract the trailing index (e.g., '_2') from a figure name, or return ''."""
        if not name:
            return ""
        index_match = re.search(r"_(\d+)$", name)
        if index_match:
            return index_match.group(1)
        return ""
