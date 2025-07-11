import json
import psycopg2
import configparser
import uuid
import time
import re

def generate_uuid7():
    unix_ts_ms = int(time.time() * 1000)
    ts_bytes = unix_ts_ms.to_bytes(6, byteorder='big')
    random_bytes = uuid.uuid4().bytes[6:]
    uuid_bytes = ts_bytes + random_bytes
    uuid_bytes = (
        uuid_bytes[0:6] +
        bytes([((uuid_bytes[6] & 0x0F) | 0x70)]) +
        uuid_bytes[7:]
    )
    uuid_bytes = (
        uuid_bytes[0:8] +
        bytes([((uuid_bytes[8] & 0x3F) | 0x80)]) +
        uuid_bytes[9:]
    )
    return str(uuid.UUID(bytes=uuid_bytes))

def normalize_color(color):
    return color.strip().lower() if color else None

def normalize_font(font):
    if not font:
        return 'roboto'
    return ''.join(c if c.isalnum() or c == '_' else '_' for c in font.strip().lower().replace(' ', '_').replace('-', '_'))

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

def ensure_presentation_layout(cur, presentation_layout_id):
    cur.execute('SELECT 1 FROM "PresentationLayout" WHERE id=%s', (presentation_layout_id,))
    if not cur.fetchone():
        cur.execute('''
            INSERT INTO "PresentationLayout" (id, name)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        ''', (presentation_layout_id, f'auto_inserted_{presentation_layout_id[:8]}'))

def get_blocklayoutconfig_id(cur):
    cur.execute('SELECT id FROM "BlockLayoutConfig" LIMIT 1')
    row = cur.fetchone()
    if not row:
        raise Exception("No BlockLayoutConfig row found")
    return row[0]

def get_palette_id(cur, presentation_layout_id, color):
    cur.execute('SELECT id FROM "PresentationPalette" WHERE "presentationLayoutId"=%s AND color=%s', (presentation_layout_id, color))
    row = cur.fetchone()
    if row:
        return row[0]
    ensure_presentation_layout(cur, presentation_layout_id)
    palette_id = generate_uuid7()
    cur.execute('INSERT INTO "PresentationPalette" (id, "presentationLayoutId", color) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING', (palette_id, presentation_layout_id, color))
    return palette_id

def ensure_array_value(cur, table, column, id_col, id_val, value, typecast):
    cur.execute(f'''
        UPDATE "{table}"
        SET {column} = array_append({column}, %s::{typecast})
        WHERE {id_col} = %s AND NOT (%s::{typecast} = ANY({column}))
    ''', (value, id_val, value))

def get_array_index(cur, table, column, id_col, id_val, value, typecast):
    cur.execute(f'''
        SELECT array_position({column}, %s::{typecast}) - 1 FROM "{table}" WHERE {id_col} = %s
    ''', (value, id_val))
    idx = cur.fetchone()
    return idx[0] if idx else None

def main():
    with open('my_output/sql_generator_input.json', encoding='utf-8') as f:
        slides = json.load(f)

    conn = get_db_connection()
    cur = conn.cursor()
    blocklayoutconfig_id = get_blocklayoutconfig_id(cur)

    # Maintain mappings from Figma IDs to generated uuid7s
    figma_block_to_uuid = {}
    figma_slide_to_uuid = {}

    for slide in slides:
        presentation_layout_id = slide['presentation_layout_id']
        slide_layout_number = slide['slide_layout_number']
        slide_layout_name = slide['slide_layout_name']
        slide_config = slide.get('slideConfig', {})
        if not slide_config:
            continue

        # Generate or reuse uuid7 for this slide
        figma_slide_id = slide.get('slide_layout_id') or slide_layout_name
        if figma_slide_id not in figma_slide_to_uuid:
            figma_slide_to_uuid[figma_slide_id] = generate_uuid7()
        slide_layout_uuid = figma_slide_to_uuid[figma_slide_id]

        # Map block type to blockLayoutId (from blocks)
        block_type_to_id = {}
        figure_name_to_id = {}
        for block in slide['blocks']:
            # Generate or reuse uuid7 for this block
            if block['id'] not in figma_block_to_uuid:
                figma_block_to_uuid[block['id']] = generate_uuid7()
            block_uuid = figma_block_to_uuid[block['id']]
            block_type_to_id[block['type']] = block_uuid
            if block['type'] == 'figure':
                m = re.search(r'\(([^)]+)\)', block['name'])
                if m:
                    figure_name_to_id[m.group(1)] = block_uuid

        for block_type, color_dict in slide_config.items():
            for color_hex, obj_list in color_dict.items():
                color_hex_norm = normalize_color(color_hex)
                ensure_array_value(cur, "BlockLayoutConfig", block_type, "id", blocklayoutconfig_id, color_hex_norm, "text")
                palette_id = get_palette_id(cur, presentation_layout_id, color_hex_norm)
                for obj in obj_list:
                    color = normalize_color(obj.get('color', color_hex_norm))
                    font = normalize_font(obj.get('fontFamily', 'roboto'))
                    ensure_array_value(cur, "BlockLayoutConfig", "font", "id", blocklayoutconfig_id, font, '"FontFamilyType"')
                    color_idx = get_array_index(cur, "BlockLayoutConfig", block_type, "id", blocklayoutconfig_id, color_hex_norm, "text")
                    font_idx = get_array_index(cur, "BlockLayoutConfig", "font", "id", blocklayoutconfig_id, font, '"FontFamilyType"')
                    if block_type == 'figure':
                        figure_name = obj.get('figureName')
                        block_layout_id = figure_name_to_id.get(figure_name)
                        if not block_layout_id:
                            continue
                    else:
                        block_layout_id = block_type_to_id.get(block_type)
                        if not block_layout_id:
                            continue
                    block_layout_index_config_id = generate_uuid7()
                    cur.execute('''
                        INSERT INTO "BlockLayoutIndexConfig" (id, "blockLayoutId", "indexColorId", "indexFontId")
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    ''', (block_layout_index_config_id, block_layout_id, color_idx, font_idx))
                    slide_layout_index_config_id = generate_uuid7()
                    cur.execute('''
                        INSERT INTO "SlideLayoutIndexConfig" (id, "presentationPaletteId", "configNumber", "slideLayoutId", "blockLayoutIndexConfigId", "blockLayoutConfigId")
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    ''', (slide_layout_index_config_id, palette_id, 0, slide_layout_uuid, block_layout_index_config_id, blocklayoutconfig_id))

    conn.commit()
    cur.close()
    conn.close()
    print("Color/font pipeline completed.")

if __name__ == "__main__":
    main() 