import re
import glob
import uuid
import os
from color_config import (
    INDEX_COLOR_IDS_WITH_OUTLINE, INDEX_COLOR_IDS_WITHOUT_OUTLINE, INDEX_FONT_IDS, CONFIG_NUMBERS, FIGURE_INDEXES_BY_CONFIG,
    PRESENTATION_PALETTE_IDS, BLOCK_LAYOUT_CONFIG_IDS
)

# --- CONFIG ---
SQL_OUTPUT_DIR = "my_sql_output"
OUTPUT_DIR = "color_sql_output"
OUTPUT_SQL_FILE = os.path.join(OUTPUT_DIR, "index_mapping_output.sql")
DEBUG_LOG_FILE = os.path.join(OUTPUT_DIR, "debug.log")

OUTLINE_KEYWORDS = ["outline", "обводка", "контур", "stroke", "border"]

def generate_uuid():
    return str(uuid.uuid4())

def parse_sql_file(filepath):
    slides = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    slide_layout_match = re.search(r'INSERT INTO "SlideLayout".*?VALUES\s*\(\s*\'([^\']+)', content, re.DOTALL)
    slide_layout_id = slide_layout_match.group(1) if slide_layout_match else None
    block_layouts = []
    block_layout_section = re.search(r'INSERT INTO "BlockLayout".*?VALUES(.*?)RETURNING \*;', content, re.DOTALL)
    if block_layout_section:
        for match in re.finditer(r"\('([^']+)',\s*'([^']+)',\s*'([^']+)'::\"BlockLayoutType\"\)", block_layout_section.group(1)):
            block_layouts.append({
                "block_layout_id": match.group(1),
                "slide_layout_id": match.group(2),
                "block_type": match.group(3)
            })
    figures = []
    figure_section = re.search(r'INSERT INTO "Figure".*?VALUES(.*?)RETURNING \*;', content, re.DOTALL)
    if figure_section:
        for match in re.finditer(r"\('([^']+)',\s*'([^']+)',\s*'([^']+)'\)", figure_section.group(1)):
            figures.append({
                "figure_id": match.group(1),
                "block_layout_id": match.group(2),
                "figure_name": match.group(3)
            })
    return {
        "slide_layout_id": slide_layout_id,
        "block_layouts": block_layouts,
        "figures": figures
    }

def has_outline(figures):
    return any(
        any(kw in fig["figure_name"].lower() for kw in OUTLINE_KEYWORDS)
        for fig in figures
    )

def main():
    all_data = []
    file_paths = []
    for sql_file in glob.glob(f"{SQL_OUTPUT_DIR}/**/*.sql", recursive=True):
        all_data.append(parse_sql_file(sql_file))
        file_paths.append(os.path.relpath(sql_file, start=SQL_OUTPUT_DIR))
    debug_lines = []
    debug_lines.append(f"Found {len(all_data)} slides from {len(file_paths)} files.")
    for i, slide in enumerate(all_data):
        debug_lines.append(f"File: {file_paths[i]}, SlideLayoutId: {slide['slide_layout_id']}, Blocks: {len(slide['block_layouts'])}")

    # Extract all unique figure names and write config snippet
    unique_figure_names = set()
    for slide in all_data:
        for fig in slide["figures"]:
            if fig["figure_name"]:
                unique_figure_names.add(fig["figure_name"])
    unique_figure_names = sorted(unique_figure_names)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "figure_config_snippet.txt"), "w", encoding="utf-8") as f:
        for config_num in CONFIG_NUMBERS:
            f.write(f"{config_num}: {{\n")
            for name in unique_figure_names:
                f.write(f'    "{name}": 0,\n')
            f.write("}\n\n")

    blocklayoutindex_sqls = []
    slidelayoutindex_sqls = []
    blocklayoutindex_count = 0
    slidelayoutindex_count = 0
    for palette_idx, (PALETTE_ID, BLOCK_LAYOUT_CONFIG_ID) in enumerate(zip(PRESENTATION_PALETTE_IDS, BLOCK_LAYOUT_CONFIG_IDS)):
        for config_idx, config_number in enumerate(CONFIG_NUMBERS):
            for slide_idx, slide in enumerate(all_data):
                slide_layout_id = slide["slide_layout_id"]
                figures = slide["figures"]
                outline_present = has_outline(figures)
                figure_name_by_block_id = {f["block_layout_id"]: f["figure_name"] for f in figures}
                rel_path = file_paths[slide_idx]
                for block in slide["block_layouts"]:
                    block_layout_id = block["block_layout_id"]
                    block_type = block["block_type"]
                    block_comment_lines = [
                        f"\n-- path: {os.path.join(SQL_OUTPUT_DIR, rel_path)}",
                        f"-- slideLayoutId: {slide_layout_id}",
                        f"-- blockLayoutId: {block_layout_id}",
                        f"-- blockType: {block_type}"
                    ]
                    if block_type == "figure":
                        figure_name = figure_name_by_block_id.get(block_layout_id)
                        color_index = FIGURE_INDEXES_BY_CONFIG[config_number].get(figure_name, 0)
                        font_index = INDEX_FONT_IDS[config_idx]
                        if figure_name:
                            block_comment_lines.append(f"-- figureName: {figure_name}")
                    else:
                        if outline_present:
                            color_index = INDEX_COLOR_IDS_WITH_OUTLINE[config_idx]
                        else:
                            color_index = INDEX_COLOR_IDS_WITHOUT_OUTLINE[config_idx]
                        font_index = INDEX_FONT_IDS[config_idx]
                    blocklayoutindex_id = generate_uuid()
                    blocklayoutindex_sqls.append(
                        "\n".join(block_comment_lines) +
                        "\nINSERT INTO \"BlockLayoutIndexConfig\" (\n"
                        "    \"id\",\n"
                        "    \"blockLayoutId\",\n"
                        "    \"indexColorId\",\n"
                        "    \"indexFontId\"\n"
                        ") VALUES (\n"
                        f"    '{{blocklayoutindex_id}}',\n"
                        f"    '{{block_layout_id}}',\n"
                        f"    {{color_index}},\n"
                        f"    {{font_index}}\n"
                        ");\n".format(
                            blocklayoutindex_id=blocklayoutindex_id,
                            block_layout_id=block_layout_id,
                            color_index=color_index,
                            font_index=font_index
                        )
                    )
                    blocklayoutindex_count += 1
                    slide_comment_lines = [
                        f"\n-- path: {os.path.join(SQL_OUTPUT_DIR, rel_path)}",
                        f"-- slideLayoutId: {slide_layout_id}",
                        f"-- blockLayoutId: {block_layout_id}"
                    ]
                    slidelayoutindex_id = generate_uuid()
                    slidelayoutindex_sqls.append(
                        "\n".join(slide_comment_lines) +
                        "\nINSERT INTO \"SlideLayoutIndexConfig\" (\n"
                        "    \"id\",\n"
                        "    \"presentationPaletteId\",\n"
                        "    \"configNumber\",\n"
                        "    \"slideLayoutId\",\n"
                        "    \"blockLayoutIndexConfigId\",\n"
                        "    \"blockLayoutConfigId\"\n"
                        ") VALUES (\n"
                        f"    '{{slidelayoutindex_id}}',\n"
                        f"    '{{PALETTE_ID}}',\n"
                        f"    {{config_number}},\n"
                        f"    '{{slide_layout_id}}',\n"
                        f"    '{{blocklayoutindex_id}}',\n"
                        f"    '{{BLOCK_LAYOUT_CONFIG_ID}}'\n"
                        ");\n".format(
                            slidelayoutindex_id=slidelayoutindex_id,
                            PALETTE_ID=PALETTE_ID,
                            config_number=config_number,
                            slide_layout_id=slide_layout_id,
                            blocklayoutindex_id=blocklayoutindex_id,
                            BLOCK_LAYOUT_CONFIG_ID=BLOCK_LAYOUT_CONFIG_ID
                        )
                    )
                    slidelayoutindex_count += 1
    summary = f"""-- SQL Index Mapping Output
--
-- BlockLayoutIndexConfig records: {blocklayoutindex_count}
-- SlideLayoutIndexConfig records: {slidelayoutindex_count}
--
-- Each BlockLayoutIndexConfig maps a blockLayoutId to a color/font index for a config.
-- Each SlideLayoutIndexConfig connects a slideLayoutId, palette, and config to a BlockLayoutIndexConfig and BlockLayoutConfig.
--
-- Comments above each insert show the path to the original SQL file, slideLayoutId, blockLayoutId, blockType, and figureName (if any).
--
"""
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_SQL_FILE, "w", encoding="utf-8") as f:
        f.write(summary)
        for sql in blocklayoutindex_sqls + slidelayoutindex_sqls:
            f.write(sql + "\n\n")
    with open(DEBUG_LOG_FILE, "w", encoding="utf-8") as logf:
        for line in debug_lines:
            logf.write(line + "\n")
    # No print to stdout

if __name__ == "__main__":
    main() 