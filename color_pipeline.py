import json
import psycopg2
import configparser
import os
import re
from collections import defaultdict
import argparse
import time
import uuid
import logging

def normalize_color(color):
    return color.strip().lower() if color else None

def normalize_font(font):
    if not font:
        return 'roboto'
    return ''.join(c if c.isalnum() or c == '_' else '_' for c in font.strip().lower().replace(' ', '_').replace('-', '_'))

def normalize_slide_name(name):
    # Lowercase, strip, and remove 'z-index ...' suffix
    return re.sub(r'\s*z-index\s*\d+\s*$', '', name.strip().lower())

def get_db_connection():
    config = configparser.ConfigParser()
    config.read('database.ini')
    db = config['postgresql']
    return psycopg2.connect(
        dbname=db['database'],
        user=db['user'],
        password=db['password'],
        host=db['host'],
        port=db.get('port', 5432)
    )

def parse_sql_files(sql_dir):
    block_name_to_id = {}
    slide_name_to_id = {}
    figure_name_to_block_id = defaultdict(dict)
    slide_layout_name_to_file = {}
    block_pattern = re.compile(r"INSERT INTO \"BlockLayout\" \(id,.*?name.*?\) VALUES \('([\w-]+)'.*?'(.*?)'\)", re.DOTALL)
    slide_pattern = re.compile(r"INSERT INTO \"SlideLayout\" \(id,.*?name.*?\) VALUES \('([\w-]+)'.*?'(.*?)'\)", re.DOTALL)
    figure_pattern = re.compile(r"INSERT INTO \"Figure\" \(id, blockLayoutId, name\) VALUES \('([\w-]+)', '([\w-]+)', '(.*?)'\)")
    logging.info(f"Recursively searching for SQL files in: {sql_dir}")
    for root, _, files in os.walk(sql_dir):
        for fname in files:
            if not fname.endswith('.sql'):
                continue
            fpath = os.path.join(root, fname)
            logging.info(f"Parsing SQL file: {fpath}")
            # Extract slide layout name from filename (before last _Jul...)
            base = os.path.splitext(fname)[0]
            # Find last _Jul or _Aug or _Sep etc. (month abbreviation)
            m = re.search(r'_(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[0-9_\-]*$', base, re.IGNORECASE)
            if m:
                slide_layout_name_from_file = base[:m.start()]
            else:
                slide_layout_name_from_file = base
            norm_name_from_file = normalize_slide_name(slide_layout_name_from_file)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Find the SlideLayout insert block
                slide_insert_idx = content.find('INSERT INTO "SlideLayout"')
                if slide_insert_idx == -1:
                    logging.info(f"No SlideLayout INSERT in {fpath}.")
                    continue
                # Find the VALUES block after the SlideLayout insert
                values_idx = content.find('VALUES', slide_insert_idx)
                if values_idx == -1:
                    logging.info(f"No VALUES for SlideLayout in {fpath}.")
                    continue
                # Extract the lines in the VALUES block (between the first '(' after VALUES and the matching ')')
                values_start = content.find('(', values_idx)
                values_end = content.find(')', values_start)
                if values_start == -1 or values_end == -1:
                    logging.info(f"Could not find parentheses for VALUES in {fpath}.")
                    continue
                values_block = content[values_start+1:values_end]
                # Split by commas, strip whitespace and quotes
                values = [v.strip().strip("'\"") for v in values_block.split(',')]
                if len(values) < 2:
                    logging.info(f"Not enough values in VALUES block in {fpath}: {values}")
                    continue
                slide_id, slide_name = values[0], values[1]
                slide_name_to_id[norm_name_from_file] = slide_id
                slide_layout_name_to_file[norm_name_from_file] = fpath
                for m in block_pattern.finditer(content):
                    block_id, block_name = m.groups()
                    block_name_to_id[block_name.strip().lower()] = block_id
                for m in figure_pattern.finditer(content):
                    _, block_id, figure_name = m.groups()
                    if m_slide:
                        figure_name_to_block_id[norm_name_from_file][figure_name.strip().lower()] = block_id
    logging.info("Slide layout names and IDs parsed from SQL files:")
    for k, v in slide_name_to_id.items():
        logging.info(f"  [SQL] {repr(k)} -> {v}")
    return block_name_to_id, slide_name_to_id, figure_name_to_block_id, slide_layout_name_to_file

def get_blocklayoutconfig_id(cur):
    cur.execute('SELECT id FROM "BlockLayoutConfig" LIMIT 1')
    row = cur.fetchone()
    if not row:
        raise Exception("No BlockLayoutConfig row found")
    return row[0]

def get_palette_ids(cur):
    cur.execute('SELECT id, "presentationLayoutId", color FROM "PresentationPalette"')
    return {(row[1], row[2]): row[0] for row in cur.fetchall()}

def get_blocklayoutconfig_arrays(cur, blocklayoutconfig_id):
    cur.execute('SELECT * FROM "BlockLayoutConfig" WHERE id=%s', (blocklayoutconfig_id,))
    desc = [d[0] for d in cur.description]
    row = cur.fetchone()
    if not row:
        raise Exception("No BlockLayoutConfig row found")
    arrays = dict(zip(desc, row))
    return arrays

def generate_uuid7() -> str:
    """
    Generate a UUID version 7 (time-ordered UUID)
    Implementation based on the draft RFC for UUID v7 - time-ordered
    """
    # Get current UNIX timestamp (milliseconds)
    unix_ts_ms = int(time.time() * 1000)

    # Convert to bytes (48 bits for timestamp)
    ts_bytes = unix_ts_ms.to_bytes(6, byteorder='big')

    # Generate 74 random bits (9 bytes with 2 bits used for version and variant)
    random_bytes = uuid.uuid4().bytes[6:]

    # Create the UUID combining timestamp and random bits
    # First 6 bytes from timestamp, rest from random
    uuid_bytes = ts_bytes + random_bytes

    # Set the version (7) in the 6th byte
    uuid_bytes = (
        uuid_bytes[0:6] +
        bytes([((uuid_bytes[6] & 0x0F) | 0x70)]) +
        uuid_bytes[7:]
    )

    # Set the variant (RFC 4122) in the 8th byte
    uuid_bytes = (
        uuid_bytes[0:8] +
        bytes([((uuid_bytes[8] & 0x3F) | 0x80)]) +
        uuid_bytes[9:]
    )

    return str(uuid.UUID(bytes=uuid_bytes))

def main():
    parser = argparse.ArgumentParser(description="Color pipeline SQL generator")
    parser.add_argument('--sql-dir', type=str, default='my_sql_output', help='Directory containing slide SQL files (default: my_sql_output)')
    args = parser.parse_args()
    sql_dir = args.sql_dir
    color_dir = 'my_output/color_insertion'
    os.makedirs(color_dir, exist_ok=True)
    block_name_to_id, slide_name_to_id, figure_name_to_block_id, slide_layout_name_to_file = parse_sql_files(sql_dir)
    logging.info("Parsed slide layout names from SQL files:")
    for name in slide_name_to_id:
        logging.info(f"  [SQL] {repr(name)}")
    with open('my_output/sql_generator_input.json', encoding='utf-8') as f:
        slides = json.load(f)
    conn = get_db_connection()
    cur = conn.cursor()
    blocklayoutconfig_id = get_blocklayoutconfig_id(cur)
    palette_ids = get_palette_ids(cur)
    blocklayout_arrays = get_blocklayoutconfig_arrays(cur, blocklayoutconfig_id)
    for slide in slides:
        slide_layout_name = normalize_slide_name(slide['slide_layout_name'])
        logging.info(f"Processing slide_layout_name from JSON: {repr(slide_layout_name)}")
        logging.info(f"Looking for slide_layout_name: {repr(slide_layout_name)} in {list(map(repr, slide_name_to_id.keys()))}")
        slide_layout_id = slide_name_to_id.get(slide_layout_name)
        if not slide_layout_id:
            logging.warning(f"Skipping: No matching slide_layout_id for {repr(slide_layout_name)}")
            continue
        presentation_layout_id = slide['presentation_layout_id']
        blocks = slide['blocks']
        slide_config = slide.get('slideConfig', {})
        if not slide_config:
            logging.warning(f"Skipping: slideConfig is empty for '{slide_layout_name}'")
            continue
        # --- NEW: Parse the SQL file for this slide to build block/figure mappings ---
        sql_path = slide_layout_name_to_file.get(slide_layout_name)
        block_type_to_id = {}
        figure_name_to_id = {}
        if sql_path:
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                # BlockLayout: (id, slideLayoutId, blockLayoutType)
                block_pattern = re.compile(r"INSERT INTO \"BlockLayout\" \([^)]+\)\s*VALUES\s*([^)]+)\)", re.DOTALL)
                block_rows = re.findall(r"\('([\w-]+)', '[\w-]+', '([a-zA-Z]+)'::\"BlockLayoutType\"\)", sql_content)
                for block_id, block_type in block_rows:
                    block_type_to_id[block_type.lower()] = block_id
                # Figure: (id, blockLayoutId, name)
                figure_rows = re.findall(r"\('([\w-]+)', '([\w-]+)', '([^']+)'\)", sql_content)
                for fig_id, block_id, fig_name in figure_rows:
                    figure_name_to_id[fig_name.strip().lower()] = block_id
        else:
            logging.warning(f"No SQL file found for slide '{slide_layout_name}'")
        sql_lines = []
        # Track new colors/fonts to append
        new_colors = defaultdict(set)
        new_fonts = set()
        new_palette = set()
        for block_type, color_dict in slide_config.items():
            for color_hex, obj_list in color_dict.items():
                color_hex_norm = normalize_color(color_hex)
                arr = blocklayout_arrays.get(block_type, [])
                if color_hex_norm not in arr:
                    new_colors[block_type].add(color_hex_norm)
                if (presentation_layout_id, color_hex_norm) not in palette_ids:
                    new_palette.add((presentation_layout_id, color_hex_norm))
                for obj in obj_list:
                    font = normalize_font(obj.get('fontFamily', 'roboto'))
                    arr_font = blocklayout_arrays.get('font', [])
                    if font not in arr_font:
                        new_fonts.add(font)
        # Generate SQL for new colors/fonts/palette
        for block_type, colors in new_colors.items():
            for color in colors:
                sql_lines.append(f"UPDATE \"BlockLayoutConfig\" SET {block_type} = array_append({block_type}, '{color}'::text) WHERE id = '{blocklayoutconfig_id}' AND NOT ('{color}'::text = ANY({block_type}));")
        for font in new_fonts:
            sql_lines.append(f"UPDATE \"BlockLayoutConfig\" SET font = array_append(font, '{font}'::\"FontFamilyType\") WHERE id = '{blocklayoutconfig_id}' AND NOT ('{font}'::\"FontFamilyType\" = ANY(font));")
        for pres_id, color in new_palette:
            sql_lines.append(f"INSERT INTO \"PresentationPalette\" (id, \"presentationLayoutId\", color) VALUES ('{generate_uuid7()}', '{pres_id}', '{color}') ON CONFLICT DO NOTHING;")
        arrays_sim = {k: list(v) if isinstance(v, list) else list(v) for k, v in blocklayout_arrays.items()}
        # Ensure all new colors are in arrays_sim before index lookups
        for block_type, colors in new_colors.items():
            for color in colors:
                if color not in arrays_sim.setdefault(block_type, []):
                    arrays_sim[block_type].append(color)
        # Ensure all new fonts are in arrays_sim before index lookups
        for font in new_fonts:
            if font not in arrays_sim.setdefault('font', []):
                arrays_sim['font'].append(font)
        # Now safe to do index lookups
        for block_type, color_dict in slide_config.items():
            for color_hex, obj_list in color_dict.items():
                color_hex_norm = normalize_color(color_hex)
                if color_hex_norm not in arrays_sim.get(block_type, []):
                    logging.warning(f"Skipping: color '{color_hex_norm}' not in arrays_sim[{block_type}] for slide '{slide_layout_name}'")
                    continue
                color_idx = arrays_sim.get(block_type, []).index(color_hex_norm)
                for obj in obj_list:
                    font = normalize_font(obj.get('fontFamily', 'roboto'))
                    if font not in arrays_sim.get('font', []):
                        logging.warning(f"Skipping: font '{font}' not in arrays_sim['font'] for slide '{slide_layout_name}'")
                        continue
                    font_idx = arrays_sim.get('font', []).index(font)
                    if block_type == 'figure':
                        figure_name = obj.get('figureName', '').strip().lower()
                        block_layout_id = figure_name_to_id.get(figure_name)
                        if not block_layout_id:
                            logging.warning(f"Skipping: No block_layout_id for figure '{figure_name}' in slide '{slide_layout_name}'")
                            continue
                    else:
                        block_layout_id = block_type_to_id.get(block_type.lower())
                        if not block_layout_id:
                            logging.warning(f"Skipping: No block_layout_id for block_type '{block_type}' in slide '{slide_layout_name}'")
                            continue
                    sql_lines.append(f"INSERT INTO \"BlockLayoutIndexConfig\" (id, \"blockLayoutId\", \"indexColorId\", \"indexFontId\") VALUES ('{generate_uuid7()}', '{block_layout_id}', {color_idx}, {font_idx}) ON CONFLICT DO NOTHING;")
                    palette_id = palette_ids.get((presentation_layout_id, color_hex_norm), generate_uuid7())
                    sql_lines.append(f"INSERT INTO \"SlideLayoutIndexConfig\" (id, \"presentationPaletteId\", \"configNumber\", \"slideLayoutId\", \"blockLayoutIndexConfigId\", \"blockLayoutConfigId\") VALUES ('{generate_uuid7()}', '{palette_id}', 0, '{slide_layout_id}', currval(pg_get_serial_sequence('BlockLayoutIndexConfig','id')), '{blocklayoutconfig_id}') ON CONFLICT DO NOTHING;")
        # --- Output file path fix ---
        if sql_path:
            parent_dir = os.path.dirname(sql_path)
            parts = parent_dir.split(os.sep)
            # Replace the last occurrence of 'slide_insertion' with 'color_insertion'
            for i in range(len(parts)-1, -1, -1):
                if parts[i] == 'slide_insertion':
                    parts[i] = 'color_insertion'
                    break
            color_dir = os.sep.join(parts)
            os.makedirs(color_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(sql_path))[0]
            out_path = os.path.join(color_dir, f"{base_name}_color.sql")
        else:
            color_dir = 'my_output/color_insertion'
            os.makedirs(color_dir, exist_ok=True)
            base_name = slide_layout_name.replace(' ', '_')
            out_path = os.path.join(color_dir, f"{base_name}_color.sql")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sql_lines))
        logging.info(f"Wrote color SQL for slide '{slide_layout_name}' to {out_path}")
    cur.close()
    conn.close()
    logging.info("Color/font pipeline SQL generation completed.")

if __name__ == "__main__":
    # Set up logging to file at the same level as slide_insertion.log
    log_path = os.path.join(os.path.dirname(__file__), 'color_pipeline.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_path, mode='w', encoding='utf-8')]
    )
    logger = logging.getLogger(__name__)
    main() 