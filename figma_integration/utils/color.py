import math


class ColorUtils:
    @staticmethod
    def extract_color_info(node: dict) -> tuple[str | None, str | None]:
        """
        Extracts the first visible fill color/gradient and its variable/style from a Figma node.
        Returns (hex_or_gradient_color, color_variable_id, gradient_css).
        """

        fills = node.get("fills")
        if fills and isinstance(fills, list):
            fill = fills[0]

            fill_type = fill.get("type")

            if fill_type == "SOLID" and fill.get("visible", True) and "color" in fill:
                c = fill["color"]
                r = int(round(c.get("r", 0) * 255))
                g = int(round(c.get("g", 0) * 255))
                b = int(round(c.get("b", 0) * 255))
                a = fill.get("opacity", c.get("a", 1))
                if a < 1:
                    hex_or_gradient_color = f"#{r:02x}{g:02x}{b:02x}{int(a * 255):02x}"
                else:
                    hex_or_gradient_color = f"#{r:02x}{g:02x}{b:02x}"
                color_variable = None
                if "boundVariables" in fill and "color" in fill["boundVariables"]:
                    color_variable = fill["boundVariables"]["color"].get("id")
                elif "fillStyleId" in fill:
                    color_variable = fill["fillStyleId"]
                return hex_or_gradient_color, color_variable

            elif fill.get("visible", True) and fill_type in ["GRADIENT_LINEAR", "GRADIENT_RADIAL", "GRADIENT_ANGULAR", "GRADIENT_DIAMOND"]:
                hex_or_gradient_color = ColorUtils._create_gradient_css(fill)
                color_variable = None

                if "boundVariables" in fill and "color" in fill["boundVariables"]:
                    color_variable = fill["boundVariables"]["color"].get("id")
                elif "fillStyleId" in fill:
                    color_variable = fill["fillStyleId"]
                return hex_or_gradient_color, color_variable

        color = node.get("color")
        if color and isinstance(color, str):
            return color.lower(), None
        return None, None

    @staticmethod
    def _create_gradient_css(fill: dict) -> str:
        """
        Creates CSS gradient string from Figma gradient fill.
        """
        gradient_type = fill.get("type")
        gradient_stops = fill.get("gradientStops", [])
        gradient_handle_positions = fill.get("gradientHandlePositions", [])

        if not gradient_stops:
            return ""

        css_stops = []
        for stop in gradient_stops:
            color = stop.get("color", {})
            position = stop.get("position", 0)

            r = int(round(color.get("r", 0) * 255))
            g = int(round(color.get("g", 0) * 255))
            b = int(round(color.get("b", 0) * 255))
            a = color.get("a", 1)

            if a < 1:
                hex_color = f"#{r:02x}{g:02x}{b:02x}{int(a * 255):02x}"
            else:
                hex_color = f"#{r:02x}{g:02x}{b:02x}"

            percentage = int(position * 100)
            css_stops.append(f"{hex_color} {percentage}%")

        if gradient_type == "GRADIENT_LINEAR":
            angle = ColorUtils._calculate_linear_angle(gradient_handle_positions)
            return f"linear-gradient({angle}deg\\, {'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_RADIAL":
            return f"radial-gradient(circle\\, {'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_ANGULAR":
            return f"conic-gradient({'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_DIAMOND":
            return f"radial-gradient(ellipse at center\\, {'\\, '.join(css_stops)})"

        return ""

    @staticmethod
    def _calculate_linear_angle(handle_positions: list) -> int:
        """
        Calculate the angle for linear gradient from handle positions.
        Returns angle in degrees (0-360).
        """
        if len(handle_positions) < 2:
            return 0

        start = handle_positions[0]
        end = handle_positions[1]

        dx = end.get("x", 0) - start.get("x", 0)
        dy = end.get("y", 0) - start.get("y", 0)

        angle_rad = math.atan2(dy, dx)

        angle_deg = math.degrees(angle_rad)
        angle_deg = (angle_deg + 360) % 360

        return int(angle_deg)
