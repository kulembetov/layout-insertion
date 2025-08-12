"""
Script to generate DELETE and UPDATE statements by parsing existing SQL files.
Loops through SQL files in folders, extracts layout IDs, queries database,
and generates cleanup statements before the INSERT operations.
"""

import argparse
import configparser
import logging
import os
import re
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import psycopg2


class ExtractedData(TypedDict):
    slide_layout_ids: set[str]
    block_layout_ids: set[str]
    figure_ids: set[str]
    precompiled_image_ids: set[str]
    block_layout_index_config_ids: set[str]
    slide_layout_index_config_ids: set[str]
    presentation_layout_id: str | None
    slide_layout_names: set[str]


class SlideLayoutInfo(TypedDict):
    original_id: str
    name: str
    number: int
    presentation_layout_id: str


class UserBlockLayout(TypedDict):
    id: str
    parentLayoutId: str | None


class SlideLayoutIndexConfig(TypedDict):
    id: str
    slideLayoutId: str
    blockLayoutConfigId: str
    blockLayoutIndexConfigId: str
    configNumber: int


class BlockLayoutIndexConfig(TypedDict):
    id: str
    blockLayoutId: str
    indexColorId: str
    indexFontId: str


class Figure(TypedDict):
    id: str
    blockLayoutId: str
    name: str


class PrecompiledImage(TypedDict):
    id: str
    blockLayoutId: str
    url: str
    color: str


class BlockLayoutStyle(TypedDict):
    blockLayoutId: str
    textVertical: str
    textHorizontal: str
    fontSize: int
    weight: str
    zIndex: int
    textTransform: str
    color: str
    fontFamily: str
    background: str


class BlockLayoutDimension(TypedDict):
    blockLayoutId: str
    x: float
    y: float
    w: float
    h: float
    rotation: float


class BlockLayoutLimit(TypedDict):
    blockLayoutId: str
    minWords: int
    maxWords: int


class BlockLayout(TypedDict):
    id: str
    slideLayoutId: str
    blockLayoutType: str


class ExistingData(TypedDict):
    user_block_layouts: list[UserBlockLayout]
    slide_layout_index_configs: list[SlideLayoutIndexConfig]
    block_layout_index_configs: list[BlockLayoutIndexConfig]
    figures: list[Figure]
    precompiled_images: list[PrecompiledImage]
    block_layout_styles: list[BlockLayoutStyle]
    block_layout_dimensions: list[BlockLayoutDimension]
    block_layout_limits: list[BlockLayoutLimit]
    block_layouts: list[BlockLayout]


def setup_logging(output_dir: str) -> logging.Logger:
    """Setup logging configuration with both file and console handlers."""
    os.makedirs(output_dir, exist_ok=True)

    logger = logging.getLogger("update_blocks")
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    detailed_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console_formatter = logging.Formatter("%(message)s")

    log_file = os.path.join(output_dir, f"update_blocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def read_database_config(config_file: str = "../database.ini") -> dict[str, str]:
    """Read database configuration from ini file."""
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Database configuration file '{config_file}' not found")

    config = configparser.ConfigParser()
    config.read(config_path)

    if "postgresql" not in config:
        raise ValueError("No [postgresql] section found in database.ini")

    return dict(config["postgresql"])


@contextmanager
def get_database_connection(db_config: dict[str, str]):
    """Context manager for database connections with proper cleanup."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=db_config.get("host", "localhost"),
            database=db_config.get("database"),
            user=db_config.get("user"),
            password=db_config.get("password"),
            port=db_config.get("port", "5432"),
        )
        yield conn
    except psycopg2.Error as e:
        raise Exception(f"Failed to connect to database: {e}")
    finally:
        if conn:
            conn.close()


def find_sql_files(base_dir: str) -> list[dict[str, str]]:
    """Find all SQL files in the directory structure."""
    sql_files = []
    base_path = Path(base_dir)

    if not base_path.exists():
        raise FileNotFoundError(f"Directory {base_dir} does not exist")

    for sql_file in base_path.rglob("*.sql"):
        if sql_file.name.startswith("00_master"):
            continue

        relative_path = sql_file.relative_to(base_path)
        folder_parts = relative_path.parts[:-1]

        sql_files.append(
            {
                "filepath": str(sql_file),
                "filename": sql_file.name,
                "folder": "/".join(folder_parts) if folder_parts else "",
                "layout_type": folder_parts[0] if folder_parts else "unknown",
            }
        )

    return sql_files


def parse_sql_file(filepath: str) -> ExtractedData:
    """Parse SQL file to extract layout IDs and other relevant data."""
    extracted_data: ExtractedData = {
        "slide_layout_ids": set(),
        "block_layout_ids": set(),
        "figure_ids": set(),
        "precompiled_image_ids": set(),
        "block_layout_index_config_ids": set(),
        "slide_layout_index_config_ids": set(),
        "presentation_layout_id": None,
        "slide_layout_names": set(),
    }

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        slide_layout_pattern = r'INSERT INTO "SlideLayout".*?VALUES\s*\(\s*\'([^\']+)\'.*?\)'
        slide_matches = re.findall(slide_layout_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in slide_matches:
            extracted_data["slide_layout_ids"].add(match)

        pres_layout_pattern = r'INSERT INTO "SlideLayout".*?\'([^\']+)\',\s*\'([^\']+)\',\s*\d+,\s*\w+,\s*\'([^\']+)\''
        pres_matches = re.findall(pres_layout_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in pres_matches:
            if len(match) >= 3:
                extracted_data["slide_layout_names"].add(match[1])
                extracted_data["presentation_layout_id"] = match[2]

        block_layout_pattern = r'INSERT INTO "BlockLayout".*?VALUES\s*(.*?)RETURNING'
        block_matches = re.findall(block_layout_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in block_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["block_layout_ids"].update(ids)

        figure_pattern = r'INSERT INTO "Figure".*?VALUES\s*(.*?)RETURNING'
        figure_matches = re.findall(figure_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in figure_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["figure_ids"].update(ids)

        precompiled_pattern = r'INSERT INTO "PrecompiledImage".*?VALUES\s*(.*?)RETURNING'
        precompiled_matches = re.findall(precompiled_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in precompiled_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["precompiled_image_ids"].update(ids)

        block_index_pattern = r'INSERT INTO "BlockLayoutIndexConfig".*?VALUES\s*(.*?)RETURNING'
        block_index_matches = re.findall(block_index_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in block_index_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["block_layout_index_config_ids"].update(ids)

        slide_index_pattern = r'INSERT INTO "SlideLayoutIndexConfig".*?VALUES\s*(.*?)RETURNING'
        slide_index_matches = re.findall(slide_index_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in slide_index_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["slide_layout_index_config_ids"].update(ids)

    except Exception as e:
        print(f"Warning: Error parsing {filepath}: {e}")

    return extracted_data


def query_existing_slide_layout(conn, slide_name: str, slide_number: int, presentation_layout_id: str) -> str | None:
    """Find existing SlideLayout by name and number, return its ID."""
    with conn.cursor() as cursor:
        query = """
        SELECT id FROM "SlideLayout"
        WHERE name = %s AND number = %s AND "presentationLayoutId" = %s
        """
        cursor.execute(query, (slide_name, slide_number, presentation_layout_id))
        result = cursor.fetchone()
        return result[0] if result else None


def replace_slide_layout_id_in_sql(original_content: str, old_slide_id: str, new_slide_id: str) -> str:
    """Replace all occurrences of old slide layout ID with new (existing) one."""
    updated_content = original_content.replace(f"'{old_slide_id}'", f"'{new_slide_id}'")
    return updated_content


def extract_slide_layout_info(content: str) -> SlideLayoutInfo | None:
    """Extract slide layout name, number, and presentation layout ID from SQL content."""
    pattern = r'INSERT INTO "SlideLayout".*?VALUES\s*\(\s*\'([^\']+)\',\s*\'([^\']+)\',\s*([^,]+),\s*[^,]*,\s*\'([^\']+)\''
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if match:
        try:
            number_str = match.group(3).strip()
            if number_str.startswith("-"):
                number = int(number_str)
            else:
                number = int(number_str)

            return SlideLayoutInfo(
                original_id=match.group(1),
                name=match.group(2),
                number=number,
                presentation_layout_id=match.group(4),
            )
        except (ValueError, IndexError):
            return None
    return None


def remove_slide_layout_insert(content: str, existing_slide_layout_id: str) -> str:
    """Remove SlideLayout INSERT statement and replace with comment about reusing existing one."""
    slide_insert_patterns = [
        r'-- Create SlideLayout\s*\n\s*INSERT INTO "SlideLayout".*?RETURNING \*;',
        r'-- Create SlideLayout\s*INSERT INTO "SlideLayout".*?RETURNING \*;',
        r'INSERT INTO "SlideLayout".*?RETURNING \*;',
    ]

    replacement_comment = f"-- Using existing SlideLayout ID: {existing_slide_layout_id}\n-- SlideLayout INSERT statement removed (reusing existing layout)"

    modified_content = content
    for pattern in slide_insert_patterns:
        if re.search(pattern, modified_content, re.DOTALL | re.IGNORECASE):
            modified_content = re.sub(
                pattern,
                replacement_comment,
                modified_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            break

    return modified_content


def build_in_clause(ids: list[str]) -> str:
    """Helper function to safely build IN clauses for SQL queries."""
    if not ids:
        return ""
    escaped_ids = [id_val.replace("'", "''") for id_val in ids]
    return "','".join(escaped_ids)


def query_existing_data(conn, extracted_data: ExtractedData) -> ExistingData:
    """Query database for existing data that needs to be cleaned up."""
    existing_data: ExistingData = {
        "user_block_layouts": [],
        "slide_layout_index_configs": [],
        "block_layout_index_configs": [],
        "figures": [],
        "precompiled_images": [],
        "block_layout_styles": [],
        "block_layout_dimensions": [],
        "block_layout_limits": [],
        "block_layouts": [],
    }

    with conn.cursor() as cursor:
        try:
            if extracted_data["block_layout_ids"]:
                block_ids_str = build_in_clause(list(extracted_data["block_layout_ids"]))
                cursor.execute(
                    f"""
                    SELECT id, "parentLayoutId"
                    FROM "UserBlockLayout"
                    WHERE "parentLayoutId" IN ('{block_ids_str}')
                """,
                )
                existing_data["user_block_layouts"] = [UserBlockLayout(id=row[0], parentLayoutId=row[1]) for row in cursor.fetchall()]

            if extracted_data["slide_layout_index_config_ids"]:
                config_ids_str = build_in_clause(list(extracted_data["slide_layout_index_config_ids"]))
                cursor.execute(
                    f"""
                    SELECT id, "slideLayoutId", "blockLayoutConfigId", "blockLayoutIndexConfigId", "configNumber"
                    FROM "SlideLayoutIndexConfig"
                    WHERE id IN ('{config_ids_str}')
                """
                )
                existing_data["slide_layout_index_configs"] = [
                    SlideLayoutIndexConfig(
                        id=row[0],
                        slideLayoutId=row[1],
                        blockLayoutConfigId=row[2],
                        blockLayoutIndexConfigId=row[3],
                        configNumber=row[4],
                    )
                    for row in cursor.fetchall()
                ]

            if extracted_data["block_layout_index_config_ids"]:
                config_ids_str = build_in_clause(list(extracted_data["block_layout_index_config_ids"]))
                cursor.execute(
                    f"""
                    SELECT id, "blockLayoutId", "indexColorId", "indexFontId"
                    FROM "BlockLayoutIndexConfig"
                    WHERE id IN ('{config_ids_str}')
                """
                )
                existing_data["block_layout_index_configs"] = [
                    BlockLayoutIndexConfig(
                        id=row[0],
                        blockLayoutId=row[1],
                        indexColorId=row[2],
                        indexFontId=row[3],
                    )
                    for row in cursor.fetchall()
                ]

            if extracted_data["figure_ids"]:
                figure_ids_str = build_in_clause(list(extracted_data["figure_ids"]))
                cursor.execute(
                    f"""
                    SELECT id, "blockLayoutId", name
                    FROM "Figure"
                    WHERE id IN ('{figure_ids_str}')
                """
                )
                existing_data["figures"] = [Figure(id=row[0], blockLayoutId=row[1], name=row[2]) for row in cursor.fetchall()]

            if extracted_data["precompiled_image_ids"]:
                image_ids_str = build_in_clause(list(extracted_data["precompiled_image_ids"]))
                cursor.execute(
                    f"""
                    SELECT id, "blockLayoutId", url, color
                    FROM "PrecompiledImage"
                    WHERE id IN ('{image_ids_str}')
                """
                )
                existing_data["precompiled_images"] = [PrecompiledImage(id=row[0], blockLayoutId=row[1], url=row[2], color=row[3]) for row in cursor.fetchall()]

            if extracted_data["block_layout_ids"]:
                block_ids_str = build_in_clause(list(extracted_data["block_layout_ids"]))
                cursor.execute(
                    f"""
                    SELECT "blockLayoutId", "textVertical", "textHorizontal", "fontSize", "weight",
                           "zIndex", "textTransform", "color", "fontFamily", "background"
                    FROM "BlockLayoutStyles"
                    WHERE "blockLayoutId" IN ('{block_ids_str}')
                """
                )
                existing_data["block_layout_styles"] = [
                    BlockLayoutStyle(
                        blockLayoutId=row[0],
                        textVertical=row[1],
                        textHorizontal=row[2],
                        fontSize=row[3],
                        weight=row[4],
                        zIndex=row[5],
                        textTransform=row[6],
                        color=row[7],
                        fontFamily=row[8],
                        background=row[9],
                    )
                    for row in cursor.fetchall()
                ]

            if extracted_data["block_layout_ids"]:
                cursor.execute(
                    f"""
                    SELECT "blockLayoutId", x, y, w, h, rotation
                    FROM "BlockLayoutDimensions"
                    WHERE "blockLayoutId" IN ('{block_ids_str}')
                """
                )
                existing_data["block_layout_dimensions"] = [
                    BlockLayoutDimension(
                        blockLayoutId=row[0],
                        x=row[1],
                        y=row[2],
                        w=row[3],
                        h=row[4],
                        rotation=row[5],
                    )
                    for row in cursor.fetchall()
                ]

            if extracted_data["block_layout_ids"]:
                cursor.execute(
                    f"""
                    SELECT "blockLayoutId", "minWords", "maxWords"
                    FROM "BlockLayoutLimit"
                    WHERE "blockLayoutId" IN ('{block_ids_str}')
                """
                )
                existing_data["block_layout_limits"] = [BlockLayoutLimit(blockLayoutId=row[0], minWords=row[1], maxWords=row[2]) for row in cursor.fetchall()]

            if extracted_data["block_layout_ids"]:
                cursor.execute(
                    f"""
                    SELECT id, "slideLayoutId", "blockLayoutType"
                    FROM "BlockLayout"
                    WHERE id IN ('{block_ids_str}')
                """
                )
                existing_data["block_layouts"] = [BlockLayout(id=row[0], slideLayoutId=row[1], blockLayoutType=row[2]) for row in cursor.fetchall()]

        except Exception as e:
            print(f"Error querying existing data: {e}")
            raise

    return existing_data


def generate_cleanup_statements(existing_data: ExistingData, logger: logging.Logger | None = None) -> list[str]:
    """Generate DELETE and UPDATE statements to clean up existing data, grouped by table for faster execution."""
    statements = []

    user_block_updates = 0
    user_block_ids = []
    for record in existing_data.get("user_block_layouts", []):
        if record["parentLayoutId"]:
            user_block_ids.append(record["id"])
            user_block_updates += 1

    if user_block_ids:
        ids_str = build_in_clause(user_block_ids)
        statements.append(f'UPDATE "UserBlockLayout" SET "parentLayoutId" = NULL WHERE id IN (\'{ids_str}\');')

        if logger:
            logger.info(f"    Will generate 1 grouped UPDATE statement for {user_block_updates} UserBlockLayout records")
        else:
            print(f"    Will generate 1 grouped UPDATE statement for {user_block_updates} UserBlockLayout records")

    slide_index_ids = [record["id"] for record in existing_data.get("slide_layout_index_configs", [])]
    if slide_index_ids:
        ids_str = build_in_clause(slide_index_ids)
        statements.append(f"DELETE FROM \"SlideLayoutIndexConfig\" WHERE id IN ('{ids_str}');")
        if logger:
            logger.info(f"    Will generate 1 grouped DELETE statement for {len(slide_index_ids)} SlideLayoutIndexConfig records")
        else:
            print(f"    Will generate 1 grouped DELETE statement for {len(slide_index_ids)} SlideLayoutIndexConfig records")

    block_index_ids = [record["id"] for record in existing_data.get("block_layout_index_configs", [])]
    if block_index_ids:
        ids_str = build_in_clause(block_index_ids)
        statements.append(f"DELETE FROM \"BlockLayoutIndexConfig\" WHERE id IN ('{ids_str}');")
        if logger:
            logger.info(f"    Will generate 1 grouped DELETE statement for {len(block_index_ids)} BlockLayoutIndexConfig records")
        else:
            print(f"    Will generate 1 grouped DELETE statement for {len(block_index_ids)} BlockLayoutIndexConfig records")

    figure_ids = [record["id"] for record in existing_data.get("figures", [])]
    if figure_ids:
        ids_str = build_in_clause(figure_ids)
        statements.append(f"DELETE FROM \"Figure\" WHERE id IN ('{ids_str}');")
        if logger:
            logger.info(f"    Will generate 1 grouped DELETE statement for {len(figure_ids)} Figure records")
        else:
            print(f"    Will generate 1 grouped DELETE statement for {len(figure_ids)} Figure records")

    precompiled_ids = [record["id"] for record in existing_data.get("precompiled_images", [])]
    if precompiled_ids:
        ids_str = build_in_clause(precompiled_ids)
        statements.append(f"DELETE FROM \"PrecompiledImage\" WHERE id IN ('{ids_str}');")
        if logger:
            logger.info(f"    Will generate 1 grouped DELETE statement for {len(precompiled_ids)} PrecompiledImage records")
        else:
            print(f"    Will generate 1 grouped DELETE statement for {len(precompiled_ids)} PrecompiledImage records")

    block_style_ids = [record["blockLayoutId"] for record in existing_data.get("block_layout_styles", [])]
    if block_style_ids:
        ids_str = build_in_clause(block_style_ids)
        statements.append(f'DELETE FROM "BlockLayoutStyles" WHERE "blockLayoutId" IN (\'{ids_str}\');')
        if logger:
            logger.info(f"    Will generate 1 grouped DELETE statement for {len(block_style_ids)} BlockLayoutStyles records")
        else:
            print(f"    Will generate 1 grouped DELETE statement for {len(block_style_ids)} BlockLayoutStyles records")

    block_dimension_ids = [record["blockLayoutId"] for record in existing_data.get("block_layout_dimensions", [])]
    if block_dimension_ids:
        ids_str = build_in_clause(block_dimension_ids)
        statements.append(f'DELETE FROM "BlockLayoutDimensions" WHERE "blockLayoutId" IN (\'{ids_str}\');')
        if logger:
            logger.info(f"    Will generate 1 grouped DELETE statement for {len(block_dimension_ids)} BlockLayoutDimensions records")
        else:
            print(f"    Will generate 1 grouped DELETE statement for {len(block_dimension_ids)} BlockLayoutDimensions records")

    block_limit_ids = [record["blockLayoutId"] for record in existing_data.get("block_layout_limits", [])]
    if block_limit_ids:
        ids_str = build_in_clause(block_limit_ids)
        statements.append(f'DELETE FROM "BlockLayoutLimit" WHERE "blockLayoutId" IN (\'{ids_str}\');')
        if logger:
            logger.info(f"    Will generate 1 grouped DELETE statement for {len(block_limit_ids)} BlockLayoutLimit records")
        else:
            print(f"    Will generate 1 grouped DELETE statement for {len(block_limit_ids)} BlockLayoutLimit records")

    block_layout_ids = [record["id"] for record in existing_data.get("block_layouts", [])]
    if block_layout_ids:
        ids_str = build_in_clause(block_layout_ids)
        statements.append(f"DELETE FROM \"BlockLayout\" WHERE id IN ('{ids_str}');")
        if logger:
            logger.info(f"    Will generate 1 grouped DELETE statement for {len(block_layout_ids)} BlockLayout records")
        else:
            print(f"    Will generate 1 grouped DELETE statement for {len(block_layout_ids)} BlockLayout records")

    total_operations = user_block_updates + len(slide_index_ids) + len(block_index_ids) + len(figure_ids) + len(precompiled_ids) + len(block_style_ids) + len(block_dimension_ids) + len(block_limit_ids) + len(block_layout_ids)

    if logger:
        logger.info(f"    Total cleanup operations: {total_operations}")
        logger.info(f"    Total SQL statements: {len(statements)} (grouped for faster execution)")
        logger.info("    NOTE: Keeping SlideLayout and its related tables - only cleaning up BlockLayout records")
    else:
        print(f"    Total cleanup operations: {total_operations}")
        print(f"    Total SQL statements: {len(statements)} (grouped for faster execution)")
        print("    NOTE: Keeping SlideLayout and its related tables - only cleaning up BlockLayout records")

    return statements


def generate_cleanup_sql_file(
    sql_file_info: dict[str, str],
    cleanup_statements: list[str],
    new_file_content: str,
    output_dir: str,
    existing_data: ExistingData,
    existing_slide_layout_id: str | None = None,
    logger: logging.Logger | None = None,
) -> str | None:
    """Generate a cleanup SQL file with DELETE/UPDATE statements followed by INSERT statements from the NEW file."""

    if not cleanup_statements:
        if logger:
            logger.info(f"No cleanup needed for {sql_file_info['filename']}")
        else:
            print(f"No cleanup needed for {sql_file_info['filename']}")
        return None

    output_folder = os.path.join(output_dir, sql_file_info["folder"]) if sql_file_info["folder"] else output_dir
    os.makedirs(output_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%b%d_%H-%M")
    base_name = sql_file_info["filename"].replace(".sql", "")
    new_filename = f"cleanup_{base_name}_{timestamp}.sql"
    output_path = os.path.join(output_folder, new_filename)

    user_block_updates = len([s for s in cleanup_statements if 'UPDATE "UserBlockLayout"' in s])
    delete_operations = len(cleanup_statements) - user_block_updates

    total_records = 0
    for stmt in cleanup_statements:
        if 'UPDATE "UserBlockLayout"' in stmt:
            ids_match = re.search(r"IN \('([^']+)'\)", stmt)
            if ids_match:
                ids_str = ids_match.group(1)
                total_records += len(ids_str.split("','"))
        elif "DELETE FROM" in stmt:
            ids_match = re.search(r"IN \('([^']+)'\)", stmt)
            if ids_match:
                ids_str = ids_match.group(1)
                total_records += len(ids_str.split("','"))

    processed_content = new_file_content
    slide_info = extract_slide_layout_info(new_file_content)

    if slide_info and existing_slide_layout_id:
        if slide_info["original_id"] != existing_slide_layout_id:
            if logger:
                logger.info(f"    Replacing SlideLayout ID: {slide_info['original_id']} → {existing_slide_layout_id}")
            else:
                print(f"    Replacing SlideLayout ID: {slide_info['original_id']} → {existing_slide_layout_id}")
            processed_content = replace_slide_layout_id_in_sql(new_file_content, slide_info["original_id"], existing_slide_layout_id)

        processed_content = remove_slide_layout_insert(processed_content, existing_slide_layout_id)

    sql_content = []

    sql_content.extend(
        [
            f"-- Cleanup and insert for {sql_file_info['filename']}",
            f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"-- Layout Type: {sql_file_info['layout_type']}",
            "",
            "-- Statistics:",
            f"--   UserBlockLayout updates (parentLayoutId → NULL): {user_block_updates}",
            f"--   DELETE operations: {delete_operations}",
            f"--   Total SQL statements: {len(cleanup_statements)}",
            f"--   Total records affected: {total_records}",
            f"--   Using existing SlideLayout ID: {existing_slide_layout_id or 'N/A'}",
            "",
            "BEGIN;",
            "",
        ]
    )

    if cleanup_statements:
        update_statements = [s for s in cleanup_statements if 'UPDATE "UserBlockLayout"' in s]
        delete_statements = [s for s in cleanup_statements if "DELETE FROM" in s]

        if update_statements:
            sql_content.extend(update_statements)
            sql_content.append("")

        if delete_statements:
            delete_by_table: dict[str, list[str]] = {}
            for stmt in delete_statements:
                table_match = re.search(r'DELETE FROM "([^"]+)"', stmt)
                if table_match:
                    table_name = table_match.group(1)
                    if table_name not in delete_by_table:
                        delete_by_table[table_name] = []
                    delete_by_table[table_name].append(stmt)

            table_order = [
                "SlideLayoutIndexConfig",
                "BlockLayoutIndexConfig",
                "Figure",
                "PrecompiledImage",
                "BlockLayoutStyles",
                "BlockLayoutDimensions",
                "BlockLayoutLimit",
                "BlockLayout",
            ]

            for table_name in table_order:
                if table_name in delete_by_table:
                    stmt = delete_by_table[table_name][0]
                    ids_match = re.search(r"IN \('([^']+)'\)", stmt)
                    if ids_match:
                        ids_str = ids_match.group(1)
                        len(ids_str.split("','"))

                    sql_content.extend(delete_by_table[table_name])
                    sql_content.append("")

    cleaned_content = processed_content.strip()
    if cleaned_content.upper().startswith("BEGIN;"):
        cleaned_content = cleaned_content[6:].strip()
    if cleaned_content.upper().endswith("COMMIT;"):
        cleaned_content = cleaned_content[:-7].strip()

    sql_content.append(cleaned_content)

    sql_content.extend(
        [
            "",
            "COMMIT;",
            "",
            f"-- Summary for {sql_file_info['filename']}:",
            f"--   Existing SlideLayout ID used: {existing_slide_layout_id or 'N/A'}",
            f"--   UserBlockLayout.parentLayoutId set to NULL: {user_block_updates} records",
            f"--   Records deleted: {total_records}",
            f"--   Total SQL statements: {len(cleanup_statements)}",
        ]
    )

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sql_content))
        return output_path
    except Exception as e:
        if logger:
            logger.error(f"Failed to write SQL file {output_path}: {e}")
        else:
            print(f"Error: Failed to write SQL file {output_path}: {e}")
        return None


def find_corresponding_new_file(
    old_sql_file_info: dict[str, str],
    new_sql_folder: str,
    logger: logging.Logger | None = None,
) -> str | None:
    """Find the corresponding new SQL file for an old SQL file based on layout name and structure."""
    new_sql_path = Path(new_sql_folder)

    if not new_sql_path.exists():
        return None

    old_filename = Path(old_sql_file_info["filename"]).stem
    old_folder = old_sql_file_info["folder"]

    search_patterns = [
        old_sql_file_info["filename"],
        re.sub(r"_[A-Z][a-z]{2}\d{2}_\d{2}-\d{2}", "", old_sql_file_info["filename"]),
        f"{old_filename}.sql",
    ]

    for pattern in search_patterns:
        if old_folder:
            search_path = new_sql_path / old_folder / pattern
        else:
            search_path = new_sql_path / pattern

        if search_path.exists():
            if logger:
                logger.info(f"    Found corresponding new file: {search_path}")
            return str(search_path)

    base_name_without_timestamp = re.sub(r"_[A-Z][a-z]{2}\d{2}_\d{2}-\d{2}", "", old_filename)

    if old_folder:
        folder_path = new_sql_path / old_folder
    else:
        folder_path = new_sql_path

    if folder_path.exists():
        for new_file in folder_path.glob("*.sql"):
            new_filename = new_file.stem
            new_base_name = re.sub(r"_[A-Z][a-z]{2}\d{2}_\d{2}-\d{2}", "", new_filename)

            if new_base_name == base_name_without_timestamp:
                if logger:
                    logger.info(f"    Found corresponding new file by base name: {new_file}")
                return str(new_file)

    try:
        old_content = Path(old_sql_file_info["filepath"]).read_text(encoding="utf-8")
        old_slide_info = extract_slide_layout_info(old_content)

        if old_slide_info:
            for new_file in new_sql_path.rglob("*.sql"):
                if new_file.name.startswith("00_master"):
                    continue

                try:
                    new_content = new_file.read_text(encoding="utf-8")
                    new_slide_info = extract_slide_layout_info(new_content)

                    if new_slide_info and new_slide_info["name"] == old_slide_info["name"] and new_slide_info["number"] == old_slide_info["number"]:

                        relative_path = new_file.relative_to(new_sql_path)
                        folder_parts = relative_path.parts[:-1]

                        if old_folder == "/".join(folder_parts):
                            if logger:
                                logger.info(f"    Found corresponding new file by content: {new_file}")
                            return str(new_file)

                except Exception:
                    continue

    except Exception:
        pass

    if logger:
        logger.warning(f"    No corresponding new file found for {old_sql_file_info['filename']}")
    return None


def copy_new_sql_files(
    new_sql_folder: str,
    output_dir: str,
    slide_layout_mappings: dict[str, str],
    folder_filter: str | None = None,
    logger: logging.Logger | None = None,
    processed_slide_keys: set | None = None,
) -> list[str]:
    """Copy new SQL files to output directory, replacing new UUIDs with existing SlideLayout IDs and removing SlideLayout INSERT statements. Skip files already processed in cleanup generation."""
    copied_files: list[str] = []
    new_sql_path = Path(new_sql_folder)

    if not new_sql_path.exists():
        if logger:
            logger.warning(f"New SQL folder {new_sql_folder} does not exist")
        else:
            print(f"Warning: New SQL folder {new_sql_folder} does not exist")
        return copied_files

    for sql_file in new_sql_path.rglob("*.sql"):
        if sql_file.name.startswith("00_master"):
            continue

        relative_path = sql_file.relative_to(new_sql_path)
        folder_parts = relative_path.parts[:-1]

        if folder_filter and folder_parts and folder_parts[0] != folder_filter:
            continue

        try:
            with open(sql_file, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            if logger:
                logger.error(f"Failed to read {sql_file}: {e}")
            else:
                print(f"Error: Failed to read {sql_file}: {e}")
            continue

        slide_info = extract_slide_layout_info(content)
        if not slide_info:
            if logger:
                logger.warning(f"  Skipping {relative_path} - could not extract slide layout info")
            else:
                print(f"  Skipping {relative_path} - could not extract slide layout info")
            continue

        slide_key = f"{slide_info['name']}_{slide_info['number']}_{slide_info['presentation_layout_id']}"

        if processed_slide_keys and slide_key in processed_slide_keys:
            if logger:
                logger.info(f"  Skipping {relative_path} - already processed in cleanup generation")
            else:
                print(f"  Skipping {relative_path} - already processed in cleanup generation")
            continue

        if slide_key not in slide_layout_mappings:
            if logger:
                logger.warning(f"  Skipping {relative_path} - no existing SlideLayout found")
            else:
                print(f"  Skipping {relative_path} - no existing SlideLayout found")
            continue

        existing_slide_layout_id = slide_layout_mappings[slide_key]
        if logger:
            logger.info(f"  Processing {relative_path} - replacing new UUID with existing SlideLayout ID: {existing_slide_layout_id}")
        else:
            print(f"  Processing {relative_path} - replacing new UUID with existing SlideLayout ID: {existing_slide_layout_id}")

        modified_content = replace_slide_layout_id_in_sql(content, slide_info["original_id"], existing_slide_layout_id)

        modified_content = remove_slide_layout_insert(modified_content, existing_slide_layout_id)

        output_file_path = Path(output_dir) / relative_path
        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%b%d_%H-%M")
        base_name = output_file_path.stem
        new_filename = f"new_{base_name}_{timestamp}.sql"
        final_output_path = output_file_path.parent / new_filename

        try:
            with open(final_output_path, "w", encoding="utf-8") as f:
                f.write(modified_content)
            copied_files.append(str(final_output_path))
            if logger:
                logger.info(f"  Copied and updated: {relative_path} → {new_filename}")
            else:
                print(f"  Copied and updated: {relative_path} → {new_filename}")
        except Exception as e:
            if logger:
                logger.error(f"Failed to write {final_output_path}: {e}")
            else:
                print(f"Error: Failed to write {final_output_path}: {e}")

    return copied_files


def main():
    """Main function to process SQL files and generate cleanup statements."""
    parser = argparse.ArgumentParser(description="Generate cleanup statements from existing SQL files and combine with new insertions")
    parser.add_argument(
        "old_sql_folder",
        type=str,
        help="Path to folder containing old SQL files (e.g., my_sql_output_old)",
    )
    parser.add_argument(
        "new_sql_folder",
        type=str,
        help="Path to folder containing new SQL files (e.g., my_sql_output)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="final",
        help="Output directory for combined SQL files (default: final)",
    )
    parser.add_argument(
        "--folder-filter",
        "-f",
        type=str,
        help="Filter to specific folder (e.g., 3cols)",
    )

    args = parser.parse_args()

    try:
        if os.path.exists(args.output_dir):
            print(f"Removing existing output directory: {args.output_dir}")
            shutil.rmtree(args.output_dir)

        os.makedirs(args.output_dir, exist_ok=True)

        logger = setup_logging(args.output_dir)
        logger.info("=" * 60)
        logger.info("Update Blocks Script Started")
        logger.info("=" * 60)
        logger.info(f"Old SQL folder: {args.old_sql_folder}")
        logger.info(f"New SQL folder: {args.new_sql_folder}")
        logger.info(f"Output directory: {args.output_dir}")
        if args.folder_filter:
            logger.info(f"Folder filter: {args.folder_filter}")
        logger.info("=" * 60)

        logger.info("Reading database configuration...")
        db_config = read_database_config()

        with get_database_connection(db_config) as conn:
            logger.info("Connected to database successfully.")

            logger.info(f"\n=== STEP 1: Generating cleanup statements from {args.old_sql_folder} ===")
            logger.info(f"Scanning for SQL files in {args.old_sql_folder}...")
            old_sql_files = find_sql_files(args.old_sql_folder)

            if args.folder_filter:
                old_sql_files = [f for f in old_sql_files if f["layout_type"] == args.folder_filter]

            if not old_sql_files:
                logger.warning("No old SQL files found matching criteria")
                print("No old SQL files found matching criteria")
                return 1

            logger.info(f"Found {len(old_sql_files)} old SQL files to process")
            print(f"Found {len(old_sql_files)} old SQL files to process")

            cleanup_files = []
            slide_layout_mappings = {}
            processed_slide_keys = set()
            total_cleanup_operations = 0
            processed_slides = 0
            skipped_slides = 0

            for sql_file_info in old_sql_files:
                logger.info(f"\nProcessing: {sql_file_info['filepath']}")

                corresponding_new_file = find_corresponding_new_file(sql_file_info, args.new_sql_folder, logger)

                if not corresponding_new_file:
                    logger.warning("  Skipping - no corresponding new file found")
                    skipped_slides += 1
                    continue

                try:
                    with open(corresponding_new_file, encoding="utf-8") as f:
                        new_file_content = f.read()
                except Exception as e:
                    logger.error(f"Failed to read new file {corresponding_new_file}: {e}")
                    skipped_slides += 1
                    continue

                try:
                    with open(sql_file_info["filepath"], encoding="utf-8") as f:
                        original_content = f.read()
                except Exception as e:
                    logger.error(f"Failed to read {sql_file_info['filepath']}: {e}")
                    skipped_slides += 1
                    continue

                slide_info = extract_slide_layout_info(original_content)
                if not slide_info:
                    logger.warning(f"Could not extract slide layout info from {sql_file_info['filename']}")
                    skipped_slides += 1
                    continue

                logger.info(f"  Slide Info: {slide_info['name']} (number: {slide_info['number']})")

                existing_slide_layout_id = query_existing_slide_layout(
                    conn,
                    slide_info["name"],
                    slide_info["number"],
                    slide_info["presentation_layout_id"],
                )

                if not existing_slide_layout_id:
                    logger.warning(f"  No existing SlideLayout found for '{slide_info['name']}' number {slide_info['number']}")
                    logger.warning("  Skipping this file - SlideLayout must exist in database first")
                    skipped_slides += 1
                    continue

                logger.info(f"  Found existing SlideLayout ID: {existing_slide_layout_id}")

                slide_key = f"{slide_info['name']}_{slide_info['number']}_{slide_info['presentation_layout_id']}"
                slide_layout_mappings[slide_key] = existing_slide_layout_id
                processed_slide_keys.add(slide_key)

                extracted_data = parse_sql_file(sql_file_info["filepath"])

                if slide_info["original_id"] in extracted_data["slide_layout_ids"]:
                    extracted_data["slide_layout_ids"].remove(slide_info["original_id"])
                    extracted_data["slide_layout_ids"].add(existing_slide_layout_id)

                if not any(extracted_data.values()):
                    logger.warning(f"No extractable data found in {sql_file_info['filename']}")
                    skipped_slides += 1
                    continue

                logger.info(f"  Found: {len(extracted_data['slide_layout_ids'])} slide layouts, " f"{len(extracted_data['block_layout_ids'])} block layouts")

                existing_data = query_existing_data(conn, extracted_data)

                cleanup_statements = generate_cleanup_statements(existing_data, logger)

                if not cleanup_statements:
                    logger.info(f"  No cleanup needed for {sql_file_info['filename']}")
                    processed_slides += 1
                    continue

                logger.info(f"  Generated {len(cleanup_statements)} cleanup statements")
                total_cleanup_operations += len(cleanup_statements)

                output_path = generate_cleanup_sql_file(
                    sql_file_info,
                    cleanup_statements,
                    new_file_content,
                    args.output_dir,
                    existing_data,
                    existing_slide_layout_id,
                    logger,
                )

                if output_path:
                    cleanup_files.append(output_path)
                    logger.info(f"  Generated: {output_path}")
                    processed_slides += 1

        logger.info("Database connection closed.")

        logger.info(f"\n=== STEP 2: Copying remaining new insertion statements from {args.new_sql_folder} ===")
        logger.info("Note: Files already processed in cleanup generation will be skipped")
        logger.info(f"Found {len(slide_layout_mappings)} slide layout mappings")
        new_files = copy_new_sql_files(
            args.new_sql_folder,
            args.output_dir,
            slide_layout_mappings,
            args.folder_filter,
            logger,
            processed_slide_keys,
        )

        print(f"Slides processed: {processed_slides}")
        print(f"Slides skipped: {skipped_slides}")
        print(f"Total slides found: {len(old_sql_files)}")
        print(f"Cleanup files generated: {len(cleanup_files)}")
        print(f"New files copied: {len(new_files)}")
        print(f"Total cleanup operations: {total_cleanup_operations}")
        print(f"Output directory: {args.output_dir}")
        print(f"{'='*60}")

        logger.info("\nProcessing completed!")
        logger.info(f"Generated {len(cleanup_files)} cleanup SQL files")
        logger.info(f"Copied {len(new_files)} new SQL files")
        logger.info(f"Total cleanup operations: {total_cleanup_operations}")
        logger.info(f"\nOutput directory: {args.output_dir}")
        logger.info("Files are ready for execution.")
        logger.info("=" * 60)
        logger.info("Update Blocks Script Completed Successfully")
        logger.info("=" * 60)

    except Exception as e:
        if "logger" in locals():
            logger.error(f"Error: {e}")
        else:
            print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
