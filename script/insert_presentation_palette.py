import argparse
import configparser
import csv
import json
import sys

import psycopg2
import uuid_utils as uuid


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


def parse_db_config(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    db = config["postgresql"]
    return {
        "host": db.get("host", "localhost"),
        "port": db.getint("port", 5432),
        "user": db["user"],
        "password": db["password"],
        "database": db["database"],
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
            if response in ["yes", "y"]:
                return True
            elif response in ["no", "n"]:
                print("Execution cancelled by user.")
                return False
            else:
                print("Please enter 'yes' or 'no'.")
        except KeyboardInterrupt:
            print("\n\nExecution cancelled by user.")
            return False


def collect_palette_pairs(json_path):
    with open(json_path, encoding="utf-8") as f:
        slides = json.load(f)
    pairs = set()
    for slide in slides:
        layout_id = slide.get("presentation_layout_id")
        palette_colors = slide.get("presentationPaletteColors", [])
        for color in palette_colors:
            pairs.add((layout_id, color))
    return sorted(list(pairs))


def insert_palette_auto(pairs, db_config, csv_path):
    if not psycopg2:
        print("psycopg2 is required for auto mode. Please install it.")
        sys.exit(1)
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    total = 0
    mapping = []
    for layout_id, color in pairs:
        palette_id = generate_uuid()
        total += 1
        print(f"Trying: layout_id={layout_id}, color={color} ... ", end="")
        cur.execute(
            'SELECT id FROM "PresentationPalette" WHERE "presentationLayoutId"=%s AND color=%s',
            (layout_id, color),
        )
        row = cur.fetchone()
        if row:
            print("SKIPPED (already exists)")
            mapping.append({"id": row[0], "presentationLayoutId": layout_id, "color": color})
            skipped += 1
        else:
            cur.execute(
                'INSERT INTO "PresentationPalette" (id, "presentationLayoutId", color) VALUES (%s, %s, %s)',
                (palette_id, layout_id, color),
            )
            print("INSERTED")
            mapping.append({"id": palette_id, "presentationLayoutId": layout_id, "color": color})
            inserted += 1
        conn.commit()
    print(f"Summary: Attempted {total}, Inserted {inserted}, Skipped {skipped}")
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["id", "presentationLayoutId", "color"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping)
    print(f"Mapping written to {csv_path}")
    cur.close()
    conn.close()


def insert_palette_manual(pairs, csv_path):
    mapping = []
    for layout_id, color in pairs:
        palette_id = generate_uuid()
        sql = f"INSERT INTO \"PresentationPalette\" (id, \"presentationLayoutId\", color) VALUES ('{palette_id}', '{layout_id}', '{color}');"
        print(f"{sql}")
        mapping.append({"id": palette_id, "presentationLayoutId": layout_id, "color": color})
    print(f"Summary: Generated {len(pairs)} SQL statements.")
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["id", "presentationLayoutId", "color"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping)
    print(f"Mapping written to {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Insert PresentationPalette records from sql_generator_input.json")
    parser.add_argument("--json", required=True, help="Path to sql_generator_input.json")
    parser.add_argument(
        "--mode",
        choices=["auto", "manual"],
        default="manual",
        help="Insert mode: auto (DB) or manual (print SQL)",
    )
    parser.add_argument("--db", default="database.ini", help="Path to database.ini")
    parser.add_argument(
        "--csv",
        default="presentation_palette_mapping.csv",
        help="Path to output CSV mapping file",
    )
    args = parser.parse_args()

    pairs = collect_palette_pairs(args.json)
    if args.mode == "auto":
        db_config = parse_db_config(args.db)
        if not confirm_db_execution(db_config):
            sys.exit(0)
        insert_palette_auto(pairs, db_config, args.csv)
    else:
        insert_palette_manual(pairs, args.csv)


if __name__ == "__main__":
    main()
