import os
from typing import Any

import configuration as config
from configuration import Dimensions
from log_utils import logs, setup_logger

from .base import FigmaSession
from .figma_extractor import FigmaExtractor
from .filters import FilterConfig, FilterMode
from .utils.block import BlockUtils
from .utils.helper import HelpUtils
from .utils.validators import Validator

logger = setup_logger(__name__)


@logs(logger, on=True)
class FigmaToSQLIntegrator(FigmaExtractor):
    """Integrates Figma extraction with SQL generation"""

    def __init__(self, session: FigmaSession) -> None:
        super().__init__(session)

    def extract_slide_group(self, target_slides: list[int]) -> dict[str, str | dict | list | int]:
        """Extract slide group"""
        self.session._filter_config = FilterConfig(
            mode=FilterMode.SLIDE_GROUP,
            target_slides=target_slides,
            require_z_index=True,
        )
        return self.extract_data()

    def extract_slide_names(self, target_names: list[str]) -> dict[str, str | dict | list | int]:
        """Extract slides by their names"""
        self.session._filter_config = FilterConfig(mode=FilterMode.SLIDE_NAME, target_names=target_names)
        return self.extract_data()

    def extract_status(self) -> dict[str, str | dict | list | int]:
        """Extract blocks marked as ready for development."""
        self.session._filter_config = FilterConfig(mode=FilterMode.STATUS)
        return self.extract_data()

    def prepare_sql_generator_input(self, figma_data: dict[str, str | dict | list | int]) -> list[dict[str, str | int | dict | list | bool]]:
        """Convert Figma data to format suitable for SQL Generator"""
        sql_input: list[dict[str, str | int | dict | list | bool]] = []

        if not isinstance(figma_data, dict):
            return sql_input

        slides_raw = figma_data.get("slides", [])
        if not isinstance(slides_raw, list):
            return sql_input

        for slide_raw in slides_raw:
            if not isinstance(slide_raw, dict):
                continue

            slide_number_raw = slide_raw.get("slide_number")
            if not isinstance(slide_number_raw, int):
                continue

            frame_name_raw = slide_raw.get("frame_name")
            slide_type_raw = slide_raw.get("slide_type")
            if not isinstance(frame_name_raw, str) or not isinstance(slide_type_raw, str):
                continue

            # Validate slide data
            if not Validator.validate_slide_data(slide_raw):
                logger.warning(f"Invalid slide data for slide {slide_number_raw}")
                continue

            slide_input = self._create_slide_input(slide_raw, slide_number_raw, frame_name_raw, slide_type_raw)
            sql_input.append(slide_input)

        return sql_input

    def _create_slide_input(self, slide_raw: dict, slide_number: int, frame_name: str, slide_type: str) -> dict[str, str | int | dict | list | bool]:
        """Create slide input dictionary"""
        is_last = slide_number == -1
        presentation_layout_id = config.DEFAULT_VALUES.presentation_layout_id

        slide_input = {
            "slide_layout_name": frame_name,
            "slide_layout_number": slide_number,
            "slide_type": slide_type,
            "forGeneration": slide_raw.get("forGeneration", True),
            "presentation_layout_id": presentation_layout_id,
            "is_last": is_last,
            "folder_name": config.SLIDE_NUMBER_TO_FOLDER.get(slide_number, "other"),
            "imagesCount": slide_raw.get("imagesCount", 0),
            "blocks": [],
            "auto_blocks": self._get_auto_blocks_for_slide(slide_raw, is_last),
            "sql_config": {
                "needs_background": config.AUTO_BLOCKS.get("add_background", True),
                "default_color": config.DEFAULT_COLOR,
                "color_settings_id": config.DEFAULT_COLOR_SETTINGS_ID,
            },
            "slideConfig": slide_raw.get("slideConfig", {}),
            "presentationPaletteColors": slide_raw.get("presentationPaletteColors", []),
        }

        # Process blocks
        blocks_raw = slide_raw.get("blocks", [])
        if isinstance(blocks_raw, list):
            slide_config = slide_raw.get("slideConfig", {})
            for block_raw in blocks_raw:
                if isinstance(block_raw, dict):
                    # Validate block data
                    if not Validator.validate_block_data(block_raw):
                        logger.warning(f"Invalid block data in slide {slide_number}")
                        continue

                    block_input = self._create_block_input(block_raw, slide_config)
                    slide_input["blocks"].append(block_input)

        return slide_input

    def _create_block_input(self, block_raw: dict, slide_config: dict) -> dict[str, str | int | dict | list | bool]:
        """Create block input dictionary"""
        block_dict = BlockUtils.build_block_dict(block_raw, slide_config)

        return {
            "id": block_dict.get("id", ""),
            "type": block_dict.get("sql_type", ""),
            "name": block_dict.get("name", ""),
            "dimensions": block_dict.get("dimensions", {}),
            "styles": dict(block_dict.get("styles", {})),
            "needs_null_styles": block_dict.get("needs_null_styles", False),
            "needs_z_index": block_dict.get("needs_z_index", False),
            "border_radius": block_dict.get("border_radius", []),
            "sql_ready": True,
            "words": block_dict.get("words", 0),
            "figure_info": block_dict.get("figure_info", {}),
            "precompiled_image_info": block_dict.get("precompiled_image_info", {}),
        }

    def _get_auto_blocks_for_slide(self, slide: dict[str, str | int | dict | list | bool], is_last: bool) -> dict[str, str | dict]:
        """Get automatic blocks configuration for a slide"""
        auto_blocks: dict[str, str | dict] = {}

        add_background = config.AUTO_BLOCKS.get("add_background", True)
        if add_background:
            background_config = config.AUTO_BLOCKS.get("background", {})
            if isinstance(background_config, dict):
                color = background_config.get("color", "#FFFFFF")
                dimensions_obj: Dimensions | Any = background_config.get("dimensions")
                if hasattr(dimensions_obj, "x"):
                    dimensions = {
                        "x": dimensions_obj.x,
                        "y": dimensions_obj.y,
                        "w": dimensions_obj.w,
                        "h": dimensions_obj.h,
                    }
                else:
                    dimensions = {"x": 0, "y": 0, "w": 1200, "h": 675}
                auto_blocks["background"] = {
                    "type": "background",
                    "color": color,
                    "dimensions": dimensions,
                }

        return auto_blocks

    def generate_sql_for_slides(
        self,
        slide_numbers: list[int],
        output_dir: str = "",
    ):
        """Complete pipeline: extract from Figma and generate SQL"""
        if not self.session.file_id or not self.session.token:
            return

        output_dir = output_dir or config.OUTPUT_CONFIG.output_dir
        logger.info(f"Extracting slides {slide_numbers} from Figma...")

        # Prepare output directory
        self._prepare_output_directory(output_dir)

        # Extract data
        figma_data = self.extract_slide_group(slide_numbers)
        if not figma_data:
            logger.info("Failed to extract data from Figma")
            return

        # Process and save data
        slides_count = self._save_extracted_data(figma_data, output_dir)
        sql_input = self.prepare_sql_generator_input(figma_data)
        self._save_sql_data(sql_input, output_dir)

        # Generate SQL files
        self._generate_sql_files(sql_input, output_dir)
        self._generate_sql_instructions(sql_input, output_dir)

        # Log completion
        self._log_completion(slides_count, len(sql_input), output_dir)

    def _prepare_output_directory(self, output_dir: str) -> None:
        """Prepare output directory"""
        if os.path.exists(output_dir):
            import shutil

            shutil.rmtree(output_dir)
            logger.info(f"Cleaned up directory: {output_dir}")

        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")

    def _save_extracted_data(self, figma_data: dict, output_dir: str) -> int:
        """Save extracted Figma data and return slides count"""
        slides_raw = figma_data.get("slides", [])
        slides_count = len(slides_raw) if isinstance(slides_raw, list) else 0

        HelpUtils.json_dump(figma_data, f"{output_dir}/figma_extract.json")

        print(f"Extracted {slides_count} slides from Figma.")
        return slides_count

    def _save_sql_data(self, sql_input: list[dict], output_dir: str) -> None:
        """Save SQL generator input data"""
        HelpUtils.json_dump({"slides": sql_input}, f"{output_dir}/sql_generator_input.json")

    def _generate_sql_files(self, sql_input: list[dict], output_dir: str) -> None:
        """Generate individual SQL files for each slide"""
        sql_dir = f"{output_dir}/sql_files"
        HelpUtils.create_directory_structure(output_dir, ["sql_files"])

        for slide in sql_input:
            sql_content = self._create_sql_for_slide(slide)
            filename = f"slide_{slide['slide_layout_number']:02d}_{slide['slide_layout_name']}.sql"

            with open(f"{sql_dir}/{filename}", "w") as f:
                f.write(sql_content)

            logger.info(f"   Generated SQL: {filename}")

    def _create_sql_for_slide(self, slide: dict) -> str:
        """Create SQL content for a single slide"""
        lines = [
            f"-- Slide {slide['slide_layout_number']}: {slide['slide_layout_name']}",
            f"-- Type: {slide['slide_type']}",
            f"-- Blocks: {len(slide.get('blocks', []))}",
            "-- Generated from Figma extraction",
            "",
            "-- CONFIGURATION FOR SQL GENERATOR:",
            f"-- Slide Layout Name: {slide['slide_layout_name']}",
            f"-- Slide Layout Number: {slide['slide_layout_number']}",
            f"-- Slide Type: {slide['slide_type']}",
            f"-- Save For Generation: {slide.get('forGeneration', True)}",
            f"-- Is Last: {slide['is_last']}",
            f"-- Presentation Layout ID: {slide['presentation_layout_id']}",
            "",
        ]

        # Add auto blocks
        auto_blocks = slide.get("auto_blocks")
        if isinstance(auto_blocks, dict):
            lines.append("-- AUTO BLOCKS:")
            for block_name, block_config in auto_blocks.items():
                lines.append(f"--   {block_name}: {block_config}")
            lines.append("")

        # Add blocks
        lines.append("-- BLOCKS TO CREATE:")
        blocks = slide.get("blocks", [])
        for i, block in enumerate(blocks, 1):
            lines.extend(self._format_block_for_sql(block, i))

        lines.append("-- Run the SQL Generator with these parameters to create the actual SQL inserts")
        return "\n".join(lines)

    def _format_block_for_sql(self, block: dict, block_index: int) -> list[str]:
        """Format block information for SQL file"""
        lines = [
            f"-- Block {block_index}: {block['type']}",
            f"--   Name: {block['name']}",
            f"--   Dimensions: {block['dimensions']}",
            f"--   Z-Index: {block['styles'].get('zIndex', 'N/A')}",
            f"--   Styles: {block['styles']}",
        ]

        if block.get("border_radius"):
            lines.append(f"--   Border Radius: {block['border_radius']}")

        blur_radius = block["styles"].get("blur", 0)
        if blur_radius > 0:
            lines.append(f"--   Blur: {blur_radius}px")

        lines.append("")
        return lines

    def _generate_sql_instructions(self, sql_input: list[dict], output_dir: str) -> None:
        """Generate comprehensive instructions for using with SQL Generator"""
        instructions = [
            "# SQL Generator Instructions",
            "Based on extracted Figma data with full config.py compatibility",
            "=" * 60,
            "",
            "## Quick Start",
            "1. Import the config module into your SQL Generator",
            "2. Use the data from sql_generator_input.json",
            f"3. All font weights are normalized to valid values {config.VALID_FONT_WEIGHTS}",
            "4. All block types are validated against config.VALID_BLOCK_TYPES",
            "",
            "## Configuration Summary",
            f"- Default Color: {config.DEFAULT_COLOR}",
            f"- Color Settings ID: {config.DEFAULT_COLOR_SETTINGS_ID}",
            f"- Miniatures Base Path: {config.MINIATURES_BASE_PATH}",
            f"- Add Background: {config.AUTO_BLOCKS.get('add_background', True)}",
            "",
        ]

        # Add slide instructions
        for i, slide in enumerate(sql_input):
            instructions.extend(self._generate_slide_instruction(slide, i))

        instructions.extend(
            [
                "## SQL Generator Commands",
                "Run these commands in your SQL Generator:",
                "```python",
                "import config",
                "from sql_generator import SQLGenerator",
                "",
                "generator = SQLGenerator(config)",
                "# Use the extracted data to populate the generator",
                "generator.run()",
                "```",
                "",
                "## Files Generated",
                "- `figma_extract.json`: Raw Figma extraction data",
                "- `sql_generator_input.json`: Processed data ready for SQL Generator",
                "- `sql_files/`: Individual SQL configuration files for each slide",
                "- `sql_instructions.md`: This instruction file",
            ]
        )

        with open(f"{output_dir}/sql_instructions.md", "w") as f:
            f.write("\n".join(instructions))

    def _generate_slide_instruction(self, slide: dict, slide_index: int) -> list[str]:
        """Generate instruction section for a single slide"""
        instructions = [
            f"## Slide {slide_index + 1}: {slide['slide_layout_name']}",
            "**Configuration:**",
            f"- Slide Number: {slide['slide_layout_number']}",
            f"- Slide Type: {slide['slide_type']}",
            f"- Save For Generation: {slide.get('forGeneration', True)}",
            f"- Is Last: {slide['is_last']}",
            f"- Folder: {slide.get('folder_name', 'other')}",
            f"- Total Blocks: {len(slide.get('blocks', []))}",
        ]

        # Add auto blocks
        auto_blocks = slide.get("auto_blocks")
        if isinstance(auto_blocks, dict):
            instructions.append("**Auto Blocks:**")
            for block_name, block_info in auto_blocks.items():
                instructions.append(f"- {block_name.title()}: {block_info['type']}")

        # Add user blocks
        instructions.append("**User Blocks:**")
        blocks = slide.get("blocks", [])
        for j, block in enumerate(blocks, 1):
            instructions.extend(self._format_block_instruction(block, j))

        instructions.append("")
        return instructions

    def _format_block_instruction(self, block: dict, block_index: int) -> list[str]:
        """Format block for instruction file"""
        instructions = [
            f"  {block_index}. **{block['type']}** - {block['name']}",
            f"     - Dimensions: {block['dimensions']}",
            f"     - Z-Index: {block['styles'].get('zIndex', 'N/A')}",
            f"     - Null Styles: {block['needs_null_styles']}",
        ]

        if not block["needs_null_styles"]:
            styles = block["styles"]
            font_size = styles.get("fontSize") or styles.get("font_size") or "-"
            weight = styles.get("weight") or "-"
            instructions.extend(
                [
                    f"     - Font: {font_size}px, weight {weight}",
                    f"     - Alignment: {styles.get('textVertical', '-')} / {styles.get('textHorizontal', '-')}",
                ]
            )

        if block.get("border_radius"):
            instructions.append(f"     - Border Radius: {block['border_radius']}")

        blur_radius = block["styles"].get("blur", 0)
        if blur_radius > 0:
            instructions.append(f"- Blur: {blur_radius}px")

        instructions.append("")
        return instructions

    def _log_completion(self, slides_count: int, sql_count: int, output_dir: str) -> None:
        """Log completion information"""
        logger.info("\nProcessing complete!")
        logger.info(f"   Extracted {slides_count} slides")
        logger.info(f"   Generated {sql_count} SQL-ready configurations")
        logger.info(f"   Files saved to {output_dir}/")

    def validate_font_weights(self) -> dict[str, str | int | list | dict]:
        """Validate font weights across presentation"""
        if not self.session.file_id or not self.session.token:
            return {"error": "Invalid credentials"}

        all_data = self.extract_slide_group(list(range(1, 15)) + [-1])

        if not all_data:
            return {"error": "Failed to extract data"}

        if not isinstance(all_data, dict):
            return {"error": "Invalid data format"}

        slides_raw = all_data.get("slides", [])
        if not isinstance(slides_raw, list):
            return {"error": "Invalid slides format"}

        return self._analyze_font_weights(slides_raw)

    def _analyze_font_weights(self, slides_raw: list) -> dict[str, str | int | list | dict]:
        """Analyze font weights across all slides"""
        weight_analysis: dict[str, str | int | list | dict] = {
            "total_blocks": 0,
            "weight_distribution": {weight: 0 for weight in config.VALID_FONT_WEIGHTS},
            "invalid_weights_found": [],
            "slides_analyzed": len(slides_raw),
        }

        for slide in slides_raw:
            if not isinstance(slide, dict):
                continue

            blocks_raw = slide.get("blocks", [])
            if not isinstance(blocks_raw, list):
                continue

            for block in blocks_raw:
                if not isinstance(block, dict):
                    continue

                weight_analysis["total_blocks"] = weight_analysis.get("total_blocks", 0)
                if isinstance(weight_analysis["total_blocks"], int):
                    weight_analysis["total_blocks"] += 1
                self._process_block_font_weight(block, slide, weight_analysis)

        return weight_analysis

    def _process_block_font_weight(self, block: dict, slide: dict, weight_analysis: dict) -> None:
        """Process font weight for a single block"""
        styles_raw = block.get("styles", {})
        if not isinstance(styles_raw, dict):
            return

        weight_raw = styles_raw.get("weight")
        if not isinstance(weight_raw, (int, float)):
            return

        weight = int(weight_raw)

        if Validator.validate_font_weight(weight):
            weight_distribution = weight_analysis.get("weight_distribution", {})
            if isinstance(weight_distribution, dict):
                current_count = weight_distribution.get(weight, 0)
                weight_distribution[weight] = current_count + 1
        else:
            self._add_invalid_weight(weight, slide, block, weight_analysis)

    def _add_invalid_weight(self, weight: int, slide: dict, block: dict, weight_analysis: dict) -> None:
        """Add invalid weight to the analysis"""
        slide_number = slide.get("slide_number", "unknown")
        block_name = block.get("name", "unknown")
        invalid_weights = weight_analysis.get("invalid_weights_found", [])

        if isinstance(invalid_weights, list):
            invalid_weights.append(
                {
                    "slide": slide_number,
                    "block": block_name,
                    "invalid_weight": weight,
                }
            )
