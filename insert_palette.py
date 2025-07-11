import argparse
import configparser
import json
import os
import sys
import time
import uuid
from collections import defaultdict

try:
    import psycopg2
except ImportError:
    psycopg2 = None

# --- UUIDv7 generator (from slide_insertion.py) ---
def generate_uuid7() -> str:
    """
    Generate a UUID version 7 (time-ordered UUID)
    Implementation based on the draft RFC for UUID v7 - time-ordered
    """
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

# --- Read DB config from database.ini ---
def read_db_config(filename='database.ini', section='postgresql'):
    parser = configparser.ConfigParser()
    parser.read(filename)
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in {filename}')
    return db

# --- Parse JSON and collect unique (presentation_layout_id, color) pairs ---
def collect_palette_pairs(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        slides = json.load(f)
    pairs = set()
    for slide in slides:
        layout_id = slide.get('presentation_layout_id')
        colors = slide.get('presentationPaletteColors') or []
        for color in colors:
            if layout_id and color:
                pairs.add((layout_id, color.strip().lower()))
    return pairs

# --- Auto mode: insert into DB ---
def insert_palette_auto(pairs, db_config):
    if not psycopg2:
        print('psycopg2 is required for auto mode. Please install it.')
        sys.exit(1)
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    total = 0
    for layout_id, color in pairs:
        palette_id = generate_uuid7()
        total += 1
        print(f"[AUTO] Trying: layout_id={layout_id}, color={color} ... ", end='')
        cur.execute('SELECT 1 FROM "PresentationPalette" WHERE "presentationLayoutId"=%s AND color=%s', (layout_id, color))
        if cur.fetchone():
            print("SKIPPED (already exists)")
            skipped += 1
            continue
        cur.execute('INSERT INTO "PresentationPalette" (id, "presentationLayoutId", color) VALUES (%s, %s, %s)', (palette_id, layout_id, color))
        print("INSERTED")
        inserted += 1
    conn.commit()
    cur.close()
    conn.close()
    print(f"\nSummary: Attempted: {total}, Inserted: {inserted}, Skipped: {skipped}")

# --- Manual mode: print SQL ---
def print_palette_sql(pairs):
    total = 0
    for layout_id, color in pairs:
        palette_id = generate_uuid7()
        sql = f"INSERT INTO \"PresentationPalette\" (id, \"presentationLayoutId\", color) VALUES ('{palette_id}', '{layout_id}', '{color}');"
        print(f"[MANUAL] {sql}")
        total += 1
    print(f"\nSummary: Generated {total} SQL statements.")

# --- Main CLI ---
def main():
    parser = argparse.ArgumentParser(description='Insert PresentationPalette records from sql_generator_input.json')
    parser.add_argument('--json', type=str, default='my_output/sql_generator_input.json', help='Path to sql_generator_input.json')
    parser.add_argument('--mode', type=str, choices=['auto', 'manual'], default='manual', help='Mode: auto (insert) or manual (print SQL)')
    parser.add_argument('--db', type=str, default='database.ini', help='Path to database.ini')
    args = parser.parse_args()

    pairs = collect_palette_pairs(args.json)
    if not pairs:
        print('No palette pairs found.')
        return
    if args.mode == 'auto':
        db_config = read_db_config(args.db)
        insert_palette_auto(pairs, db_config)
    else:
        print_palette_sql(pairs)

if __name__ == '__main__':
    main() 