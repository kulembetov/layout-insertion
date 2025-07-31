#!/usr/bin/env python3
"""
Script to generate DELETE and UPDATE statements by parsing existing SQL files.
Loops through SQL files in folders, extracts layout IDs, queries database,
and generates cleanup statements before the INSERT operations.
"""

import configparser
import psycopg2
import os
import re
import argparse
import shutil
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any, Set
from pathlib import Path


def setup_logging(output_dir: str) -> logging.Logger:
    """Setup logging configuration with both file and console handlers."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create logger
    logger = logging.getLogger("update_blocks")
    logger.setLevel(logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter("%(message)s")

    # File handler - detailed logging to file
    log_file = os.path.join(
        output_dir, f"update_blocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)

    # Console handler - clean output to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def read_database_config(config_file: str = "../database.ini") -> Dict[str, str]:
    """Read database configuration from ini file."""
    if not os.path.exists(config_file):
        raise FileNotFoundError(
            f"Database configuration file '{config_file}' not found"
        )

    config = configparser.ConfigParser()
    config.read(config_file)

    if "postgresql" not in config:
        raise ValueError("No [postgresql] section found in database.ini")

    return dict(config["postgresql"])


def connect_to_database(db_config: Dict[str, str]):
    """Create database connection."""
    try:
        conn = psycopg2.connect(
            host=db_config.get("host", "localhost"),
            database=db_config.get("database"),
            user=db_config.get("user"),
            password=db_config.get("password"),
            port=db_config.get("port", "5432"),
        )
        return conn
    except psycopg2.Error as e:
        raise Exception(f"Failed to connect to database: {e}")


def find_sql_files(base_dir: str) -> List[Dict[str, str]]:
    """Find all SQL files in the directory structure."""
    sql_files = []
    base_path = Path(base_dir)

    if not base_path.exists():
        raise FileNotFoundError(f"Directory {base_dir} does not exist")

    # Look for SQL files in the folder structure
    for sql_file in base_path.rglob("*.sql"):
        # Skip master scripts
        if sql_file.name.startswith("00_master"):
            continue

        relative_path = sql_file.relative_to(base_path)
        folder_parts = relative_path.parts[:-1]  # All parts except filename

        sql_files.append(
            {
                "filepath": str(sql_file),
                "filename": sql_file.name,
                "folder": "/".join(folder_parts) if folder_parts else "",
                "layout_type": folder_parts[0] if folder_parts else "unknown",
            }
        )

    return sql_files


def parse_sql_file(filepath: str) -> Dict[str, Any]:
    """Parse SQL file to extract layout IDs and other relevant data."""
    extracted_data = {
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
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract SlideLayout data
        slide_layout_pattern = (
            r'INSERT INTO "SlideLayout".*?VALUES\s*\(\s*\'([^\']+)\'.*?\)'
        )
        slide_matches = re.findall(
            slide_layout_pattern, content, re.DOTALL | re.IGNORECASE
        )
        for match in slide_matches:
            extracted_data["slide_layout_ids"].add(match)

        # Extract presentation layout ID from SlideLayout INSERT
        pres_layout_pattern = r'INSERT INTO "SlideLayout".*?\'([^\']+)\',\s*\'([^\']+)\',\s*\d+,\s*\w+,\s*\'([^\']+)\''
        pres_matches = re.findall(
            pres_layout_pattern, content, re.DOTALL | re.IGNORECASE
        )
        for match in pres_matches:
            if len(match) >= 3:
                extracted_data["slide_layout_names"].add(match[1])  # name
                extracted_data["presentation_layout_id"] = match[
                    2
                ]  # presentationLayoutId

        # Extract BlockLayout IDs
        block_layout_pattern = r'INSERT INTO "BlockLayout".*?VALUES\s*(.*?)RETURNING'
        block_matches = re.findall(
            block_layout_pattern, content, re.DOTALL | re.IGNORECASE
        )
        for match in block_matches:
            # Extract individual block layout IDs from VALUES section
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["block_layout_ids"].update(ids)

        # Extract Figure IDs
        figure_pattern = r'INSERT INTO "Figure".*?VALUES\s*(.*?)RETURNING'
        figure_matches = re.findall(figure_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in figure_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["figure_ids"].update(ids)

        # Extract PrecompiledImage IDs
        precompiled_pattern = (
            r'INSERT INTO "PrecompiledImage".*?VALUES\s*(.*?)RETURNING'
        )
        precompiled_matches = re.findall(
            precompiled_pattern, content, re.DOTALL | re.IGNORECASE
        )
        for match in precompiled_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["precompiled_image_ids"].update(ids)

        # Extract BlockLayoutIndexConfig IDs
        block_index_pattern = (
            r'INSERT INTO "BlockLayoutIndexConfig".*?VALUES\s*(.*?)RETURNING'
        )
        block_index_matches = re.findall(
            block_index_pattern, content, re.DOTALL | re.IGNORECASE
        )
        for match in block_index_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["block_layout_index_config_ids"].update(ids)

        # Extract SlideLayoutIndexConfig IDs
        slide_index_pattern = (
            r'INSERT INTO "SlideLayoutIndexConfig".*?VALUES\s*(.*?)RETURNING'
        )
        slide_index_matches = re.findall(
            slide_index_pattern, content, re.DOTALL | re.IGNORECASE
        )
        for match in slide_index_matches:
            id_pattern = r"\(\'([^\']+)\'"
            ids = re.findall(id_pattern, match)
            extracted_data["slide_layout_index_config_ids"].update(ids)

    except Exception as e:
        print(f"Warning: Error parsing {filepath}: {e}")

    return extracted_data


def query_existing_slide_layout(
    conn, slide_name: str, slide_number: int, presentation_layout_id: str
) -> str:
    """Find existing SlideLayout by name and number, return its ID."""
    cursor = conn.cursor()

    query = """
    SELECT id FROM "SlideLayout" 
    WHERE name = %s AND number = %s AND "presentationLayoutId" = %s
    """
    cursor.execute(query, (slide_name, slide_number, presentation_layout_id))
    result = cursor.fetchone()
    cursor.close()

    if result:
        return result[0]
    else:
        return None


def replace_slide_layout_id_in_sql(
    original_content: str, old_slide_id: str, new_slide_id: str
) -> str:
    """Replace all occurrences of old slide layout ID with new (existing) one."""
    # Replace in all contexts where the slide layout ID appears
    updated_content = original_content.replace(f"'{old_slide_id}'", f"'{new_slide_id}'")
    return updated_content


def extract_slide_layout_info(content: str) -> Dict[str, Any]:
    """Extract slide layout name, number, and presentation layout ID from SQL content."""
    # Pattern to match SlideLayout INSERT statement
    pattern = r'INSERT INTO "SlideLayout".*?VALUES\s*\(\s*\'([^\']+)\',\s*\'([^\']+)\',\s*(\d+),\s*\w+,\s*\'([^\']+)\''
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if match:
        return {
            "original_id": match.group(1),
            "name": match.group(2),
            "number": int(match.group(3)),
            "presentation_layout_id": match.group(4),
        }
    return None


def query_existing_data(
    conn, extracted_data: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """Query database for existing data that needs to be cleaned up."""
    existing_data = {
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

    cursor = conn.cursor()

    try:
        # Query UserBlockLayout records that reference the block layouts
        if extracted_data["block_layout_ids"]:
            block_ids_str = "','".join(extracted_data["block_layout_ids"])
            cursor.execute(
                f"""
                SELECT id, "parentLayoutId" 
                FROM "UserBlockLayout" 
                WHERE "parentLayoutId" IN ('{block_ids_str}')
            """
            )
            existing_data["user_block_layouts"] = [
                {"id": row[0], "parentLayoutId": row[1]} for row in cursor.fetchall()
            ]

        # Query SlideLayoutIndexConfig records
        if extracted_data["slide_layout_index_config_ids"]:
            config_ids_str = "','".join(extracted_data["slide_layout_index_config_ids"])
            cursor.execute(
                f"""
                SELECT id, "slideLayoutId", "blockLayoutConfigId", "blockLayoutIndexConfigId", "configNumber"
                FROM "SlideLayoutIndexConfig" 
                WHERE id IN ('{config_ids_str}')
            """
            )
            existing_data["slide_layout_index_configs"] = [
                {
                    "id": row[0],
                    "slideLayoutId": row[1],
                    "blockLayoutConfigId": row[2],
                    "blockLayoutIndexConfigId": row[3],
                    "configNumber": row[4],
                }
                for row in cursor.fetchall()
            ]

        # Query BlockLayoutIndexConfig records
        if extracted_data["block_layout_index_config_ids"]:
            config_ids_str = "','".join(extracted_data["block_layout_index_config_ids"])
            cursor.execute(
                f"""
                SELECT id, "blockLayoutId", "indexColorId", "indexFontId"
                FROM "BlockLayoutIndexConfig" 
                WHERE id IN ('{config_ids_str}')
            """
            )
            existing_data["block_layout_index_configs"] = [
                {
                    "id": row[0],
                    "blockLayoutId": row[1],
                    "indexColorId": row[2],
                    "indexFontId": row[3],
                }
                for row in cursor.fetchall()
            ]

        # Query Figure records
        if extracted_data["figure_ids"]:
            figure_ids_str = "','".join(extracted_data["figure_ids"])
            cursor.execute(
                f"""
                SELECT id, "blockLayoutId", name
                FROM "Figure" 
                WHERE id IN ('{figure_ids_str}')
            """
            )
            existing_data["figures"] = [
                {"id": row[0], "blockLayoutId": row[1], "name": row[2]}
                for row in cursor.fetchall()
            ]

        # Query PrecompiledImage records
        if extracted_data["precompiled_image_ids"]:
            image_ids_str = "','".join(extracted_data["precompiled_image_ids"])
            cursor.execute(
                f"""
                SELECT id, "blockLayoutId", url, color
                FROM "PrecompiledImage" 
                WHERE id IN ('{image_ids_str}')
            """
            )
            existing_data["precompiled_images"] = [
                {"id": row[0], "blockLayoutId": row[1], "url": row[2], "color": row[3]}
                for row in cursor.fetchall()
            ]

        # Query BlockLayoutStyles records
        if extracted_data["block_layout_ids"]:
            block_ids_str = "','".join(extracted_data["block_layout_ids"])
            cursor.execute(
                f"""
                SELECT "blockLayoutId", "textVertical", "textHorizontal", "fontSize", "weight", 
                       "zIndex", "textTransform", "color", "fontFamily", "background"
                FROM "BlockLayoutStyles" 
                WHERE "blockLayoutId" IN ('{block_ids_str}')
            """
            )
            existing_data["block_layout_styles"] = [
                {
                    "blockLayoutId": row[0],
                    "textVertical": row[1],
                    "textHorizontal": row[2],
                    "fontSize": row[3],
                    "weight": row[4],
                    "zIndex": row[5],
                    "textTransform": row[6],
                    "color": row[7],
                    "fontFamily": row[8],
                    "background": row[9],
                }
                for row in cursor.fetchall()
            ]

        # Query BlockLayoutDimensions records
        if extracted_data["block_layout_ids"]:
            cursor.execute(
                f"""
                SELECT "blockLayoutId", x, y, w, h, rotation
                FROM "BlockLayoutDimensions" 
                WHERE "blockLayoutId" IN ('{block_ids_str}')
            """
            )
            existing_data["block_layout_dimensions"] = [
                {
                    "blockLayoutId": row[0],
                    "x": row[1],
                    "y": row[2],
                    "w": row[3],
                    "h": row[4],
                    "rotation": row[5],
                }
                for row in cursor.fetchall()
            ]

        # Query BlockLayoutLimit records
        if extracted_data["block_layout_ids"]:
            cursor.execute(
                f"""
                SELECT "blockLayoutId", "minWords", "maxWords"
                FROM "BlockLayoutLimit" 
                WHERE "blockLayoutId" IN ('{block_ids_str}')
            """
            )
            existing_data["block_layout_limits"] = [
                {"blockLayoutId": row[0], "minWords": row[1], "maxWords": row[2]}
                for row in cursor.fetchall()
            ]

        # Query BlockLayout records
        if extracted_data["block_layout_ids"]:
            cursor.execute(
                f"""
                SELECT id, "slideLayoutId", "blockLayoutType"
                FROM "BlockLayout" 
                WHERE id IN ('{block_ids_str}')
            """
            )
            existing_data["block_layouts"] = [
                {"id": row[0], "slideLayoutId": row[1], "blockLayoutType": row[2]}
                for row in cursor.fetchall()
            ]

    except Exception as e:
        print(f"Error querying existing data: {e}")
        raise
    finally:
        cursor.close()

    return existing_data


def generate_cleanup_statements(
    existing_data: Dict[str, List[Dict[str, Any]]], logger: logging.Logger = None
) -> List[str]:
    """Generate DELETE and UPDATE statements to clean up existing data, grouped by table for faster execution."""
    statements = []

    # Step 1: Update UserBlockLayout to set parentLayoutId to NULL
    # This is CRITICAL - we must do this first to avoid foreign key constraint violations
    user_block_updates = 0
    user_block_ids = []
    for record in existing_data.get("user_block_layouts", []):
        if record[
            "parentLayoutId"
        ]:  # Only update if parentLayoutId is not already NULL
            user_block_ids.append(record["id"])
            user_block_updates += 1

    if user_block_ids:
        # Group all UserBlockLayout updates into a single statement for faster execution
        ids_str = "','".join(user_block_ids)
        statements.append(
            f'UPDATE "UserBlockLayout" SET "parentLayoutId" = NULL WHERE id IN (\'{ids_str}\');'
        )

        if logger:
            logger.info(
                f"    Will generate 1 grouped UPDATE statement for {user_block_updates} UserBlockLayout records"
            )
        else:
            print(
                f"    Will generate 1 grouped UPDATE statement for {user_block_updates} UserBlockLayout records"
            )

    # Step 2: Delete BLOCK-related records only (keep SlideLayout and its direct dependencies)
    # Delete in correct order to avoid FK constraint violations, grouped by table for speed

    # Delete SlideLayoutIndexConfig (references slideLayoutId - these might conflict with new inserts)
    slide_index_ids = [
        record["id"] for record in existing_data.get("slide_layout_index_configs", [])
    ]
    if slide_index_ids:
        ids_str = "','".join(slide_index_ids)
        statements.append(
            f"DELETE FROM \"SlideLayoutIndexConfig\" WHERE id IN ('{ids_str}');"
        )
        if logger:
            logger.info(
                f"    Will generate 1 grouped DELETE statement for {len(slide_index_ids)} SlideLayoutIndexConfig records"
            )
        else:
            print(
                f"    Will generate 1 grouped DELETE statement for {len(slide_index_ids)} SlideLayoutIndexConfig records"
            )

    # Delete BlockLayoutIndexConfig (references blockLayoutId)
    block_index_ids = [
        record["id"] for record in existing_data.get("block_layout_index_configs", [])
    ]
    if block_index_ids:
        ids_str = "','".join(block_index_ids)
        statements.append(
            f"DELETE FROM \"BlockLayoutIndexConfig\" WHERE id IN ('{ids_str}');"
        )
        if logger:
            logger.info(
                f"    Will generate 1 grouped DELETE statement for {len(block_index_ids)} BlockLayoutIndexConfig records"
            )
        else:
            print(
                f"    Will generate 1 grouped DELETE statement for {len(block_index_ids)} BlockLayoutIndexConfig records"
            )

    # Delete Figure (references blockLayoutId)
    figure_ids = [record["id"] for record in existing_data.get("figures", [])]
    if figure_ids:
        ids_str = "','".join(figure_ids)
        statements.append(f"DELETE FROM \"Figure\" WHERE id IN ('{ids_str}');")
        if logger:
            logger.info(
                f"    Will generate 1 grouped DELETE statement for {len(figure_ids)} Figure records"
            )
        else:
            print(
                f"    Will generate 1 grouped DELETE statement for {len(figure_ids)} Figure records"
            )

    # Delete PrecompiledImage (references blockLayoutId)
    precompiled_ids = [
        record["id"] for record in existing_data.get("precompiled_images", [])
    ]
    if precompiled_ids:
        ids_str = "','".join(precompiled_ids)
        statements.append(
            f"DELETE FROM \"PrecompiledImage\" WHERE id IN ('{ids_str}');"
        )
        if logger:
            logger.info(
                f"    Will generate 1 grouped DELETE statement for {len(precompiled_ids)} PrecompiledImage records"
            )
        else:
            print(
                f"    Will generate 1 grouped DELETE statement for {len(precompiled_ids)} PrecompiledImage records"
            )

    # Delete BlockLayoutStyles (references blockLayoutId)
    block_style_ids = [
        record["blockLayoutId"]
        for record in existing_data.get("block_layout_styles", [])
    ]
    if block_style_ids:
        ids_str = "','".join(block_style_ids)
        statements.append(
            f'DELETE FROM "BlockLayoutStyles" WHERE "blockLayoutId" IN (\'{ids_str}\');'
        )
        if logger:
            logger.info(
                f"    Will generate 1 grouped DELETE statement for {len(block_style_ids)} BlockLayoutStyles records"
            )
        else:
            print(
                f"    Will generate 1 grouped DELETE statement for {len(block_style_ids)} BlockLayoutStyles records"
            )

    # Delete BlockLayoutDimensions (references blockLayoutId)
    block_dimension_ids = [
        record["blockLayoutId"]
        for record in existing_data.get("block_layout_dimensions", [])
    ]
    if block_dimension_ids:
        ids_str = "','".join(block_dimension_ids)
        statements.append(
            f'DELETE FROM "BlockLayoutDimensions" WHERE "blockLayoutId" IN (\'{ids_str}\');'
        )
        if logger:
            logger.info(
                f"    Will generate 1 grouped DELETE statement for {len(block_dimension_ids)} BlockLayoutDimensions records"
            )
        else:
            print(
                f"    Will generate 1 grouped DELETE statement for {len(block_dimension_ids)} BlockLayoutDimensions records"
            )

    # Delete BlockLayoutLimit (references blockLayoutId)
    block_limit_ids = [
        record["blockLayoutId"]
        for record in existing_data.get("block_layout_limits", [])
    ]
    if block_limit_ids:
        ids_str = "','".join(block_limit_ids)
        statements.append(
            f'DELETE FROM "BlockLayoutLimit" WHERE "blockLayoutId" IN (\'{ids_str}\');'
        )
        if logger:
            logger.info(
                f"    Will generate 1 grouped DELETE statement for {len(block_limit_ids)} BlockLayoutLimit records"
            )
        else:
            print(
                f"    Will generate 1 grouped DELETE statement for {len(block_limit_ids)} BlockLayoutLimit records"
            )

    # Delete BlockLayout (parent of above block dependencies)
    block_layout_ids = [
        record["id"] for record in existing_data.get("block_layouts", [])
    ]
    if block_layout_ids:
        ids_str = "','".join(block_layout_ids)
        statements.append(f"DELETE FROM \"BlockLayout\" WHERE id IN ('{ids_str}');")
        if logger:
            logger.info(
                f"    Will generate 1 grouped DELETE statement for {len(block_layout_ids)} BlockLayout records"
            )
        else:
            print(
                f"    Will generate 1 grouped DELETE statement for {len(block_layout_ids)} BlockLayout records"
            )

    # NOTE: We are KEEPING SlideLayout and its related tables:
    # - SlideLayout (main record)
    # - SlideLayoutAdditionalInfo
    # - SlideLayoutDimensions
    # - SlideLayoutStyles
    # - SlideLayoutIndexConfig
    # This allows us to update just the blocks within existing slide layouts

    total_operations = (
        user_block_updates
        + len(slide_index_ids)
        + len(block_index_ids)
        + len(figure_ids)
        + len(precompiled_ids)
        + len(block_style_ids)
        + len(block_dimension_ids)
        + len(block_limit_ids)
        + len(block_layout_ids)
    )

    if logger:
        logger.info(f"    Total cleanup operations: {total_operations}")
        logger.info(
            f"    Total SQL statements: {len(statements)} (grouped for faster execution)"
        )
        logger.info(
            f"    NOTE: Keeping SlideLayout and its related tables - only cleaning up BlockLayout records"
        )
    else:
        print(f"    Total cleanup operations: {total_operations}")
        print(
            f"    Total SQL statements: {len(statements)} (grouped for faster execution)"
        )
        print(
            f"    NOTE: Keeping SlideLayout and its related tables - only cleaning up BlockLayout records"
        )

    return statements


def generate_cleanup_sql_file(
    sql_file_info: Dict[str, str],
    cleanup_statements: List[str],
    original_content: str,
    output_dir: str,
    existing_data: Dict[str, List[Dict[str, Any]]],
    existing_slide_layout_id: str = None,
    logger: logging.Logger = None,
) -> str:
    """Generate a cleanup SQL file with DELETE/UPDATE statements followed by original INSERT statements."""

    if not cleanup_statements:
        if logger:
            logger.info(f"No cleanup needed for {sql_file_info['filename']}")
        else:
            print(f"No cleanup needed for {sql_file_info['filename']}")
        return None

    # Create output directory structure
    output_folder = (
        os.path.join(output_dir, sql_file_info["folder"])
        if sql_file_info["folder"]
        else output_dir
    )
    os.makedirs(output_folder, exist_ok=True)

    # Generate timestamp for new filename
    timestamp = datetime.now().strftime("%b%d_%H-%M")
    base_name = sql_file_info["filename"].replace(".sql", "")
    new_filename = f"cleanup_{base_name}_{timestamp}.sql"
    output_path = os.path.join(output_folder, new_filename)

    # Count operations by type for reporting
    user_block_updates = len(
        [s for s in cleanup_statements if 'UPDATE "UserBlockLayout"' in s]
    )
    delete_operations = len(cleanup_statements) - user_block_updates

    # Count total records affected (from the grouped statements)
    total_records = 0
    for stmt in cleanup_statements:
        if 'UPDATE "UserBlockLayout"' in stmt:
            # Count the number of IDs in the IN clause
            ids_match = re.search(r"IN \('([^']+)'\)", stmt)
            if ids_match:
                ids_str = ids_match.group(1)
                total_records += len(ids_str.split("','"))
        elif "DELETE FROM" in stmt:
            # Count the number of IDs in the IN clause
            ids_match = re.search(r"IN \('([^']+)'\)", stmt)
            if ids_match:
                ids_str = ids_match.group(1)
                total_records += len(ids_str.split("','"))

    # Process original content - extract slide layout info and replace ID if needed
    processed_content = original_content
    slide_info = extract_slide_layout_info(original_content)

    if slide_info and existing_slide_layout_id:
        if slide_info["original_id"] != existing_slide_layout_id:
            if logger:
                logger.info(
                    f"    Replacing SlideLayout ID: {slide_info['original_id']} → {existing_slide_layout_id}"
                )
            else:
                print(
                    f"    Replacing SlideLayout ID: {slide_info['original_id']} → {existing_slide_layout_id}"
                )
            processed_content = replace_slide_layout_id_in_sql(
                original_content, slide_info["original_id"], existing_slide_layout_id
            )

        # Remove SlideLayout INSERT statement since we're reusing existing one
        slide_insert_pattern = (
            r'-- Create SlideLayout\s*INSERT INTO "SlideLayout".*?RETURNING \*;'
        )
        processed_content = re.sub(
            slide_insert_pattern,
            f"-- Using existing SlideLayout ID: {existing_slide_layout_id}",
            processed_content,
            flags=re.DOTALL,
        )

    # Generate combined SQL content
    sql_content = []

    # Header
    sql_content.extend(
        [
            f"-- Cleanup and insert for {sql_file_info['filename']}",
            f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"-- Layout Type: {sql_file_info['layout_type']}",
            "",
            f"-- Cleanup Summary:",
            f"--   Strategy: Keep SlideLayout, update BlockLayout records only",
            f"--   UserBlockLayout updates (parentLayoutId → NULL): {user_block_updates}",
            f"--   DELETE operations: {delete_operations}",
            f"--   Total SQL statements: {len(cleanup_statements)} (grouped for faster execution)",
            f"--   Total records affected: {total_records}",
            f"--",
            f"--   NOTE: Using existing SlideLayout ID: {existing_slide_layout_id or 'N/A'}",
            f"--         Only BlockLayout records and their dependencies are cleaned up.",
            f"--         Statements are grouped by table for optimal performance.",
            "",
            "BEGIN;",
            "",
        ]
    )

    # Add detailed cleanup section
    if cleanup_statements:
        sql_content.extend(
            [
                "-- =====================================================",
                "-- Cleanup Phase: Remove existing conflicting data",
                "-- =====================================================",
                "",
            ]
        )

        # Separate UserBlockLayout updates from deletes for clarity
        update_statements = [
            s for s in cleanup_statements if 'UPDATE "UserBlockLayout"' in s
        ]
        delete_statements = [s for s in cleanup_statements if "DELETE FROM" in s]

        if update_statements:
            sql_content.extend(
                [
                    "-- Step 1: Set UserBlockLayout.parentLayoutId to NULL",
                    "-- This prevents foreign key constraint violations when deleting BlockLayouts",
                    "-- (Grouped for faster execution)",
                    "",
                ]
            )
            sql_content.extend(update_statements)
            sql_content.append("")

        if delete_statements:
            sql_content.extend(
                [
                    "-- Step 2: Delete existing records in dependency order",
                    "-- Order is critical to avoid foreign key constraint violations",
                    "-- (All statements are grouped by table for optimal performance)",
                    "",
                ]
            )

            # Group delete statements by table for better organization
            delete_by_table = {}
            for stmt in delete_statements:
                table_match = re.search(r'DELETE FROM "([^"]+)"', stmt)
                if table_match:
                    table_name = table_match.group(1)
                    if table_name not in delete_by_table:
                        delete_by_table[table_name] = []
                    delete_by_table[table_name].append(stmt)

            # Add deletes grouped by table with comments
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
                    # Count records in the grouped statement
                    stmt = delete_by_table[table_name][
                        0
                    ]  # Only one statement per table now
                    ids_match = re.search(r"IN \('([^']+)'\)", stmt)
                    record_count = 0
                    if ids_match:
                        ids_str = ids_match.group(1)
                        record_count = len(ids_str.split("','"))

                    sql_content.extend(
                        [
                            f"-- Delete {table_name} records ({record_count} records in 1 grouped statement)",
                        ]
                    )
                    sql_content.extend(delete_by_table[table_name])
                    sql_content.append("")

    # Add processed content (remove any existing BEGIN/COMMIT)
    cleaned_content = processed_content.strip()
    if cleaned_content.upper().startswith("BEGIN;"):
        cleaned_content = cleaned_content[6:].strip()
    if cleaned_content.upper().endswith("COMMIT;"):
        cleaned_content = cleaned_content[:-7].strip()

    sql_content.append(cleaned_content)

    # Footer with summary
    sql_content.extend(
        [
            "",
            "COMMIT;",
            "",
            f"-- =====================================================",
            f"-- Summary for {sql_file_info['filename']}",
            f"-- =====================================================",
            f"-- Strategy: Reuse existing SlideLayout, update BlockLayout records only",
            f"--",
            f"-- Existing SlideLayout ID used: {existing_slide_layout_id or 'N/A'}",
            f"-- UserBlockLayout.parentLayoutId set to NULL: {user_block_updates} records",
            f"-- Records deleted: {total_records}",
            f"-- Total SQL statements: {len(cleanup_statements)} (grouped for faster execution)",
            f"--",
            f"-- Preserved (not deleted):",
            f"--   - SlideLayout records",
            f"--   - SlideLayoutAdditionalInfo records",
            f"--   - SlideLayoutDimensions records",
            f"--   - SlideLayoutStyles records",
            f"--",
            f"-- Cleaned Up (deleted and re-inserted):",
            f"--   - BlockLayout records and all their dependencies",
            f"--   - UserBlockLayout.parentLayoutId references",
            f"-- This file is now ready to be executed safely.",
            f"-- It will clean up existing BlockLayout data and then",
            f"-- insert the new block data, while reusing the existing SlideLayout.",
            f"-- =====================================================",
        ]
    )

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_content))

    return output_path


def main():
    """Main function to process SQL files and generate cleanup statements."""
    parser = argparse.ArgumentParser(
        description="Generate cleanup statements from existing SQL files and combine with new insertions"
    )
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
        # Delete output directory if it exists and create a fresh one
        if os.path.exists(args.output_dir):
            print(f"Removing existing output directory: {args.output_dir}")
            shutil.rmtree(args.output_dir)

        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)

        # Setup logging after directory is created
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

        # Read database configuration
        logger.info("Reading database configuration...")
        db_config = read_database_config()

        # Connect to database
        logger.info("Connecting to database...")
        conn = connect_to_database(db_config)

        # Step 1: Process old SQL files to generate cleanup statements
        logger.info(
            f"\n=== STEP 1: Generating cleanup statements from {args.old_sql_folder} ==="
        )
        logger.info(f"Scanning for SQL files in {args.old_sql_folder}...")
        old_sql_files = find_sql_files(args.old_sql_folder)

        if args.folder_filter:
            old_sql_files = [
                f for f in old_sql_files if f["layout_type"] == args.folder_filter
            ]

        if not old_sql_files:
            logger.warning("No old SQL files found matching criteria")
            return 1

        logger.info(f"Found {len(old_sql_files)} old SQL files to process")

        cleanup_files = []
        slide_layout_mappings = {}  # Track which slide layouts we're updating
        total_cleanup_operations = 0

        # Process each old SQL file
        for sql_file_info in old_sql_files:
            logger.info(f"\nProcessing: {sql_file_info['filepath']}")

            # Read original SQL content first
            with open(sql_file_info["filepath"], "r", encoding="utf-8") as f:
                original_content = f.read()

            # Extract slide layout info from the SQL content
            slide_info = extract_slide_layout_info(original_content)
            if not slide_info:
                logger.warning(
                    f"Could not extract slide layout info from {sql_file_info['filename']}"
                )
                continue

            logger.info(
                f"  Slide Info: {slide_info['name']} (number: {slide_info['number']})"
            )

            # Find existing SlideLayout in database by name and number
            existing_slide_layout_id = query_existing_slide_layout(
                conn,
                slide_info["name"],
                slide_info["number"],
                slide_info["presentation_layout_id"],
            )

            if not existing_slide_layout_id:
                logger.warning(
                    f"  No existing SlideLayout found for '{slide_info['name']}' number {slide_info['number']}"
                )
                logger.warning(
                    f"  Skipping this file - SlideLayout must exist in database first"
                )
                continue

            logger.info(f"  Found existing SlideLayout ID: {existing_slide_layout_id}")

            # Store the mapping for later use
            slide_key = f"{slide_info['name']}_{slide_info['number']}_{slide_info['presentation_layout_id']}"
            slide_layout_mappings[slide_key] = existing_slide_layout_id

            # Parse SQL file to extract data (using the existing slide layout ID)
            extracted_data = parse_sql_file(sql_file_info["filepath"])

            # Replace the original slide layout ID with the existing one in extracted data
            if slide_info["original_id"] in extracted_data["slide_layout_ids"]:
                extracted_data["slide_layout_ids"].remove(slide_info["original_id"])
                extracted_data["slide_layout_ids"].add(existing_slide_layout_id)

            if not any(extracted_data.values()):
                logger.warning(
                    f"No extractable data found in {sql_file_info['filename']}"
                )
                continue

            logger.info(
                f"  Found: {len(extracted_data['slide_layout_ids'])} slide layouts, "
                f"{len(extracted_data['block_layout_ids'])} block layouts"
            )

            # Query database for existing data (using existing slide layout ID)
            existing_data = query_existing_data(conn, extracted_data)

            # Generate cleanup statements
            cleanup_statements = generate_cleanup_statements(existing_data, logger)

            if not cleanup_statements:
                logger.info(f"  No cleanup needed for {sql_file_info['filename']}")
                continue

            logger.info(f"  Generated {len(cleanup_statements)} cleanup statements")
            total_cleanup_operations += len(cleanup_statements)

            # Generate cleanup SQL file
            output_path = generate_cleanup_sql_file(
                sql_file_info,
                cleanup_statements,
                "",
                args.output_dir,
                existing_data,
                existing_slide_layout_id,
                logger,
            )

            if output_path:
                cleanup_files.append(output_path)
                logger.info(f"  Generated: {output_path}")

        conn.close()
        logger.info("Database connection closed.")

        # Step 2: Copy new SQL files (these contain the new insertion statements)
        logger.info(
            f"\n=== STEP 2: Copying new insertion statements from {args.new_sql_folder} ==="
        )
        logger.info(f"Found {len(slide_layout_mappings)} slide layout mappings")
        new_files = copy_new_sql_files(
            args.new_sql_folder,
            args.output_dir,
            slide_layout_mappings,
            args.folder_filter,
            logger,
        )

        logger.info(f"\nProcessing completed!")
        logger.info(f"Generated {len(cleanup_files)} cleanup SQL files")
        logger.info(f"Copied {len(new_files)} new SQL files")
        logger.info(f"Total cleanup operations: {total_cleanup_operations}")
        logger.info(f"\nOutput directory: {args.output_dir}")
        logger.info("Files are ready for execution.")
        logger.info("=" * 60)
        logger.info("Update Blocks Script Completed Successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

    return 0


def copy_new_sql_files(
    new_sql_folder: str,
    output_dir: str,
    slide_layout_mappings: Dict[str, str],
    folder_filter: str = None,
    logger: logging.Logger = None,
) -> List[str]:
    """Copy new SQL files to output directory, replacing new UUIDs with existing SlideLayout IDs."""
    copied_files = []
    new_sql_path = Path(new_sql_folder)

    if not new_sql_path.exists():
        if logger:
            logger.warning(f"New SQL folder {new_sql_folder} does not exist")
        else:
            print(f"Warning: New SQL folder {new_sql_folder} does not exist")
        return copied_files

    # Find all SQL files in new folder
    for sql_file in new_sql_path.rglob("*.sql"):
        # Skip master scripts
        if sql_file.name.startswith("00_master"):
            continue

        relative_path = sql_file.relative_to(new_sql_path)
        folder_parts = relative_path.parts[:-1]  # All parts except filename

        # Apply folder filter if specified
        if folder_filter and folder_parts and folder_parts[0] != folder_filter:
            continue

        # Read the SQL file content
        with open(sql_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract slide layout info from the SQL content
        slide_info = extract_slide_layout_info(content)
        if not slide_info:
            if logger:
                logger.warning(
                    f"  Skipping {relative_path} - could not extract slide layout info"
                )
            else:
                print(
                    f"  Skipping {relative_path} - could not extract slide layout info"
                )
            continue

        # Create a key to match with our mappings
        slide_key = f"{slide_info['name']}_{slide_info['number']}_{slide_info['presentation_layout_id']}"

        # Check if we have an existing SlideLayout ID for this slide
        if slide_key not in slide_layout_mappings:
            if logger:
                logger.warning(
                    f"  Skipping {relative_path} - no existing SlideLayout found"
                )
            else:
                print(f"  Skipping {relative_path} - no existing SlideLayout found")
            continue

        existing_slide_layout_id = slide_layout_mappings[slide_key]
        if logger:
            logger.info(
                f"  Processing {relative_path} - replacing new UUID with existing SlideLayout ID: {existing_slide_layout_id}"
            )
        else:
            print(
                f"  Processing {relative_path} - replacing new UUID with existing SlideLayout ID: {existing_slide_layout_id}"
            )

        # Replace the new UUID with the existing SlideLayout ID
        modified_content = content.replace(
            slide_info["original_id"], existing_slide_layout_id
        )

        # Create output directory structure
        output_file_path = Path(output_dir) / relative_path
        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the modified content
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)

        copied_files.append(str(output_file_path))
        if logger:
            logger.info(f"  Copied and updated: {relative_path}")
        else:
            print(f"  Copied and updated: {relative_path}")

    return copied_files


if __name__ == "__main__":
    exit(main())
