import argparse
import configparser
import json
import os
import sys
import uuid_utils as uuid
import csv
from collections import defaultdict

try:
    import psycopg2
except ImportError:
    psycopg2 = None

# --- DB config parser ---
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


# --- Font mapping ---
FONT_MAPPING = {
    "arial": "arial",
    "roboto": "roboto",
    "oswald": "oswald",
    "inter": "inter",
    "montserrat": "montserrat",
    "open_sans": "open_sans",
    "ubuntu": "ubuntu",
    "manrope": "manrope",
    "nunito": "nunito",
    "raleway": "raleway",
    "merriweather": "merriweather",
    "playfair_display": "playfair_display",
    "roboto_slab": "roboto_slab",
    "rubik": "rubik",
    "montserrat_alternates": "montserrat_alternates",
    "eb_garamond": "eb_garamond",
    "pt_astra_serif": "pt_astra_serif",
    "roboto_serif": "roboto_serif",
    "unbounded": "unbounded",
    "onest": "onest",
    "comfortaa": "comfortaa",
    "pacifico": "pacifico",
    "exo2": "exo2",
    "ibm_plex_sans": "ibm_plex_sans",
    "actay": "actay",
    "actay_wide": "actay_wide",
    "bounded": "bounded",
    "advaken_sans": "advaken_sans",
    "onder": "onder",
    "oktyabrina_script": "oktyabrina_script",
    "geologican": "geologican",
    "vollda": "vollda",
    "oddval": "oddval",
    "g8": "g8",
    "feature_mono": "feature_mono",
    "sberbank": "sberbank",
    "gazprom": "gazprom",
    "sbermarketing": "sbermarketing",
}

def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


def normalize_font(font_name: str) -> str:
    """Normalize font name to match schema enum, fallback to lowercased name if not in mapping."""
    return FONT_MAPPING.get(font_name.lower(), font_name.lower())


# --- Main logic ---
def collect_block_type_colors_fonts(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        slides = json.load(f)
    block_type_to_colors = defaultdict(set)
    block_type_to_fonts = defaultdict(set)
    for slide in slides:
        slide_config = slide.get("slideConfig", {})
        for block_type, color_dict in slide_config.items():
            for palette_color, obj_list in color_dict.items():
                for obj in obj_list:
                    color = obj.get("color", "#ffffff").lower()
                    font = normalize_font(obj.get("fontFamily", "roboto"))
                    block_type_to_colors[block_type].add(color)
                    block_type_to_fonts[block_type].add(font)
    return block_type_to_colors, block_type_to_fonts


def create_palette_configs(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        slides = json.load(f)
    slide = slides[0]
    palette_colors = slide.get("presentationPaletteColors", [])
    block_types = [
        "text",
        "slideTitle",
        "blockTitle",
        "email",
        "date",
        "name",
        "percentage",
        "figure",
        "icon",
        "background",
        "subTitle",
        "number",
        "logo",
    ]
    configs = []
    for palette_color in palette_colors:
        fonts = set()
        config = {"id": generate_uuid()}
        for block_type in block_types:
            color_array = None
            for slide in slides:
                slide_config = slide.get("slideConfig", {})
                color_objs = slide_config.get(block_type, {}).get(palette_color, None)
                if color_objs:
                    # Collect all unique fonts for this palette color
                    for obj in color_objs:
                        fonts.add(normalize_font(obj.get("fontFamily", "roboto")))
                    # Use the color array from the first occurrence
                    if color_array is None:
                        color_array = [
                            obj.get("color", "#ffffff").lower() for obj in color_objs
                        ]
            config[block_type] = color_array if color_array else ["#ffffff"]
        config["font"] = sorted(list(fonts))
        configs.append(config)
    return configs


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


def _as_pg_array(val):
    """Convert a list or string to a Postgres array literal with curly braces."""
    if isinstance(val, list):
        return "{" + ",".join(str(x) for x in val) + "}"
    return "{" + str(val) + "}"


def insert_block_layout_config_auto(json_path, db_config, csv_path):
    if not psycopg2:
        print("psycopg2 is required for auto mode. Please install it.")
        sys.exit(1)

    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    try:
        configs = create_palette_configs(json_path)
        mapping = []
        # Determine all block types and their font columns
        block_types = [
            "text",
            "slideTitle",
            "blockTitle",
            "email",
            "date",
            "name",
            "percentage",
            "figure",
            "icon",
            "background",
            "subTitle",
            "number",
            "logo",
        ]
        font_columns = [f"{bt}_font" for bt in block_types]
        for config in configs:
            # Check if a similar config already exists
            cur.execute(
                """
                SELECT id FROM "BlockLayoutConfig" 
                WHERE "text" = %s AND "slideTitle" = %s AND "blockTitle" = %s AND "font" = %s::"FontFamilyType"[]
                LIMIT 1
            """,
                (
                    _as_pg_array(config["text"]),
                    _as_pg_array(config["slideTitle"]),
                    _as_pg_array(config["blockTitle"]),
                    _as_pg_array(config["font"]),
                ),
            )
            existing = cur.fetchone()
            if existing:
                config_id = existing[0]
                print(f"[AUTO] Found existing config: {config_id}")
            else:
                config_id = config["id"]
                # Insert new config
                cur.execute(
                    """
                    INSERT INTO "BlockLayoutConfig" (
                        "id", "text", "slideTitle", "blockTitle", "email", "date", "name", "percentage",
                        "figure", "icon", "background", "subTitle", "number", "logo", "font"
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::"FontFamilyType"[])
                """,
                    (
                        config_id,
                        _as_pg_array(config["text"]),
                        _as_pg_array(config["slideTitle"]),
                        _as_pg_array(config["blockTitle"]),
                        _as_pg_array(config["email"]),
                        _as_pg_array(config["date"]),
                        _as_pg_array(config["name"]),
                        _as_pg_array(config["percentage"]),
                        _as_pg_array(config["figure"]),
                        _as_pg_array(config["icon"]),
                        _as_pg_array(config["background"]),
                        _as_pg_array(config["subTitle"]),
                        _as_pg_array(config["number"]),
                        _as_pg_array(config["logo"]),
                        _as_pg_array(config["font"]),
                    ),
                )
                print(f"[AUTO] Inserted new config: {config_id}")
            # Add to mapping, including all *_font columns
            mapping.append(
                {
                    "id": config_id,
                    "text": _as_pg_array(config["text"]),
                    "slideTitle": _as_pg_array(config["slideTitle"]),
                    "blockTitle": _as_pg_array(config["blockTitle"]),
                    "email": _as_pg_array(config["email"]),
                    "date": _as_pg_array(config["date"]),
                    "name": _as_pg_array(config["name"]),
                    "percentage": _as_pg_array(config["percentage"]),
                    "figure": _as_pg_array(config["figure"]),
                    "icon": _as_pg_array(config["icon"]),
                    "background": _as_pg_array(config["background"]),
                    "subTitle": _as_pg_array(config["subTitle"]),
                    "number": _as_pg_array(config["number"]),
                    "logo": _as_pg_array(config["logo"]),
                    "font": _as_pg_array(config["font"]),
                    **{col: str(config.get(col, [])) for col in font_columns},
                }
            )
        conn.commit()
        # Write mapping to CSV, including *_font columns
        # Only include BlockLayoutConfig table columns in CSV
        fieldnames = [
            "id",
            "text",
            "slideTitle",
            "blockTitle",
            "email",
            "date",
            "name",
            "percentage",
            "figure",
            "icon",
            "background",
            "subTitle",
            "number",
            "logo",
            "font",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(mapping)
        print(f"[AUTO] Mapping written to {csv_path}")
        print(f"[AUTO] Done. {len(mapping)} configs processed.")

    except Exception as e:
        print(f"[AUTO] Error: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def insert_block_layout_config_manual(json_path, csv_path):
    configs = create_palette_configs(json_path)
    mapping = []
    for config in configs:

        def format_array(arr):
            return _as_pg_array(arr)

        sql = f"""INSERT INTO "BlockLayoutConfig" (
    id, text, slideTitle, blockTitle, email, date, name, percentage,
    figure, icon, background, subTitle, number, logo, font
) VALUES (
    '{config['id']}',
    {format_array(config['text'])},
    {format_array(config['slideTitle'])},
    {format_array(config['blockTitle'])},
    {format_array(config['email'])},
    {format_array(config['date'])},
    {format_array(config['name'])},
    {format_array(config['percentage'])},
    {format_array(config['figure'])},
    {format_array(config['icon'])},
    {format_array(config['background'])},
    {format_array(config['subTitle'])},
    {format_array(config['number'])},
    {format_array(config['logo'])},
    {format_array(config['font'])}
);
"""
        print(f"[MANUAL] {sql}")
        mapping.append(
            {
                "id": config["id"],
                "text": _as_pg_array(config["text"]),
                "slideTitle": _as_pg_array(config["slideTitle"]),
                "blockTitle": _as_pg_array(config["blockTitle"]),
                "email": _as_pg_array(config["email"]),
                "date": _as_pg_array(config["date"]),
                "name": _as_pg_array(config["name"]),
                "percentage": _as_pg_array(config["percentage"]),
                "figure": _as_pg_array(config["figure"]),
                "icon": _as_pg_array(config["icon"]),
                "background": _as_pg_array(config["background"]),
                "subTitle": _as_pg_array(config["subTitle"]),
                "number": _as_pg_array(config["number"]),
                "logo": _as_pg_array(config["logo"]),
                "font": _as_pg_array(config["font"]),
            }
        )
    fieldnames = [
        "id",
        "text",
        "slideTitle",
        "blockTitle",
        "email",
        "date",
        "name",
        "percentage",
        "figure",
        "icon",
        "background",
        "subTitle",
        "number",
        "logo",
        "font",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping)
    print(f"[MANUAL] Mapping written to {csv_path}")
    print(f"[MANUAL] Done. {len(mapping)} configs processed.")


def main():
    parser = argparse.ArgumentParser(
        description="Insert BlockLayoutConfig records from sql_generator_input.json"
    )
    parser.add_argument(
        "--json", required=True, help="Path to sql_generator_input.json"
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "manual"],
        default="manual",
        help="Insert mode: auto (DB) or manual (print SQL)",
    )
    parser.add_argument("--db", default="database.ini", help="Path to database.ini")
    parser.add_argument(
        "--csv",
        default="block_layout_config_mapping.csv",
        help="Path to output CSV mapping file",
    )
    args = parser.parse_args()

    if not os.path.exists(args.json):
        print(f"Error: JSON file not found: {args.json}")
        sys.exit(1)

    block_type_to_colors, block_type_to_fonts = collect_block_type_colors_fonts(
        args.json
    )

    if not block_type_to_colors:
        print("Error: No slideConfig data found in JSON")
        sys.exit(1)

    print(f"Found {len(block_type_to_colors)} block types:")
    for bt in sorted(block_type_to_colors.keys()):
        print(
            f"  {bt}: {len(block_type_to_colors[bt])} colors, {len(block_type_to_fonts[bt])} fonts"
        )

    if args.mode == "auto":
        db_config = parse_db_config(args.db)
        if not confirm_db_execution(db_config):
            sys.exit(0)
        insert_block_layout_config_auto(args.json, db_config, args.csv)
    else:
        insert_block_layout_config_manual(args.json, args.csv)


if __name__ == "__main__":
    main()
