import argparse
import configparser
import json
import os
import sys
import time
import uuid
import csv
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
    uuid_bytes = bytearray(uuid_bytes)
    uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | (7 << 4)
    uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(uuid_bytes)))

# --- DB config parser ---
def parse_db_config(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    db = config['postgresql']
    return {
        'host': db.get('host', 'localhost'),
        'port': db.getint('port', 5432),
        'user': db['user'],
        'password': db['password'],
        'database': db['database']
    }

def confirm_db_execution(db_config):
    print("\n" + "=" * 60)
    print("CONFIRMATION REQUIRED")
    print("=" * 60)
    print(f"Database: {db_config.get('database', 'Unknown')}")
    print(f"Host: {db_config.get('host', 'Unknown')}")
    print(f"User: {db_config.get('user', 'Unknown')}")
    print("\nWARNING: This will insert records into your database!")
    print("   Make sure you have backups and understand what this script does.")
    print("=" * 60)
    while True:
        try:
            response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                print("Execution cancelled by user.")
                return False
            else:
                print("Please enter 'yes' or 'no'.")
        except KeyboardInterrupt:
            print("\n\nExecution cancelled by user.")
            return False

def collect_palette_pairs(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        slides = json.load(f)
    pairs = set()
    for slide in slides:
        layout_id = slide.get('presentation_layout_id')
        palette_colors = slide.get('presentationPaletteColors', [])
        for color in palette_colors:
            pairs.add((layout_id, color))
    return sorted(list(pairs))

def insert_palette_auto(pairs, db_config, csv_path):
    if not psycopg2:
        print('psycopg2 is required for auto mode. Please install it.')
        sys.exit(1)
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    total = 0
    mapping = []
    for layout_id, color in pairs:
        palette_id = generate_uuid7()
        total += 1
        print(f"[AUTO] Trying: layout_id={layout_id}, color={color} ... ", end='')
        cur.execute('SELECT id FROM "PresentationPalette" WHERE "presentationLayoutId"=%s AND color=%s', (layout_id, color))
        row = cur.fetchone()
        if row:
            print("SKIPPED (already exists)")
            mapping.append({'id': row[0], 'presentationLayoutId': layout_id, 'color': color})
            skipped += 1
        else:
            cur.execute('INSERT INTO "PresentationPalette" (id, "presentationLayoutId", color) VALUES (%s, %s, %s)', (palette_id, layout_id, color))
            print("INSERTED")
            mapping.append({'id': palette_id, 'presentationLayoutId': layout_id, 'color': color})
            inserted += 1
        conn.commit()
    print(f"[AUTO] Summary: Attempted {total}, Inserted {inserted}, Skipped {skipped}")
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'presentationLayoutId', 'color']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping)
    print(f"[AUTO] Mapping written to {csv_path}")
    cur.close()
    conn.close()

def insert_palette_manual(pairs, csv_path):
    mapping = []
    for layout_id, color in pairs:
        palette_id = generate_uuid7()
        sql = f'INSERT INTO "PresentationPalette" (id, "presentationLayoutId", color) VALUES (\'{palette_id}\', \'{layout_id}\', \'{color}\');'
        print(f"[MANUAL] {sql}")
        mapping.append({'id': palette_id, 'presentationLayoutId': layout_id, 'color': color})
    print(f"[MANUAL] Summary: Generated {len(pairs)} SQL statements.")
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'presentationLayoutId', 'color']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping)
    print(f"[MANUAL] Mapping written to {csv_path}")

def main():
    parser = argparse.ArgumentParser(description='Insert PresentationPalette records from sql_generator_input.json')
    parser.add_argument('--json', required=True, help='Path to sql_generator_input.json')
    parser.add_argument('--mode', choices=['auto', 'manual'], default='manual', help='Insert mode: auto (DB) or manual (print SQL)')
    parser.add_argument('--db', default='database.ini', help='Path to database.ini')
    parser.add_argument('--csv', default='presentation_palette_mapping.csv', help='Path to output CSV mapping file')
    args = parser.parse_args()

    pairs = collect_palette_pairs(args.json)
    if args.mode == 'auto':
        db_config = parse_db_config(args.db)
        if not confirm_db_execution(db_config):
            sys.exit(0)
        insert_palette_auto(pairs, db_config, args.csv)
    else:
        insert_palette_manual(pairs, args.csv)

if __name__ == '__main__':
    main() 