#!/usr/bin/env python3

import os
import csv
import uuid
import time
from datetime import datetime
from typing import List, Tuple, Dict


class SlideLayoutSQLGenerator:
    def __init__(self):
        # Arrays of indexes to loop through
        self.INDEX_COLOR_IDS = [3, 4, 5]  # Multiple color BlockLayoutIndexConfig
        self.INDEX_FONT_IDS = [0, 0, 0]   # Multiple font indexes
        self.CONFIG_NUMBERS = [0, 1, 2]   # Config numbers for SlideLayoutIndexConfig
        
        self.presentation_palette_ids = [
            '0197541e-5633-79c4-8974-de7f629c65f9',
            '0197541e-5633-795c-bd9b-ef46cddeb4d5',
            '0197541e-5633-77d8-ade6-6b34c39c62f0',
            '0197541e-5633-7a04-af49-7a4b2fe9cd02',
            '0197541e-5633-789c-832d-58af6f941855',
            '0197541e-5633-79a0-ab91-73d47bd93c67',
            '0197541e-5633-7a24-aa15-a2d29c1c8324',
            '0197541e-5633-78c8-8550-d52484a52768',
            '0197541e-5633-79e4-b65e-b03711867761',
            '0197541e-5633-78f4-9274-809d81a1645f',
            '0197541e-5633-7a44-9ca8-248ae107a83e',
            '0197541e-5633-7a64-bb7b-675a25ec8d58',
            '0197541e-562f-7a30-b343-822beec14ff0',
            '0197541e-5633-7918-b6e2-ae5a4f1653bc',
            '0197541e-5633-793c-a386-330466c622d8',
            '01973abb-48f3-7cc4-9752-4e22900b5f00',
            '01973abb-4910-7294-931c-da0dc1762ed1',
            '01973abb-48c0-7698-8fe1-871cf445d4f7'
        ]
        
        self.block_layout_config_ids = [
            '01975508-e5bd-7f3e-fa32-d5aab500d2c1',
            '01975508-e5bd-7145-3ab2-2e3f927f1303',
            '01975508-e5bd-7dba-e30c-f7e021a6d4ff',
            '01975508-e5bd-7fa4-2d8b-357ea0723ff7',
            '01975508-e5bd-7792-98d1-2716ff11f7be',
            '01975508-e5bd-7620-3b88-5d8411d6c761',
            '01975508-e5bd-79fd-6d82-b779dd29d636',
            '01975508-e5bd-77d4-02a4-e489c2988e07',
            '01975508-e5bd-7f3c-0a1a-4dda099e31b3',
            '01975508-e5bd-7ad9-4dd9-d1b8c2b9bde1',
            '01975508-e5bd-74e5-fe5f-31b40be4d512',
            '01975508-e5bd-7da3-fba9-db4a371622ab',
            '01975508-e5bd-7cc3-b684-053d80eed25e',
            '01975508-e5bd-7f5d-0c81-d637ed78437f',
            '01975508-e5bd-7991-462c-50abb5fdc8e5',
            '01973ad2-967e-7480-9bfb-a0e8757dac41',
            '01973ad2-9688-7318-8878-aab076dd9931',
            '01973ad2-9674-7d0c-b4ef-82efb91ea330'

        ]

    def read_csv_data(self, csv_file_path: str) -> List[Tuple[str, str]]:
        pairs = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    slide_layout_id = row['slidelayoutid'].strip()
                    block_layout_id = row['blocklayoutid'].strip()
                    pairs.append((slide_layout_id, block_layout_id))
            return pairs
        except Exception as e:
            raise Exception(f"Error reading CSV file: {e}")

    @staticmethod
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

    def generate_complete_sql(self, pairs: List[Tuple[str, str]]) -> str:
        # Calculate total records for each table
        unique_blocks = len(set(block_id for _, block_id in pairs))
        # Each pair × palette × config number needs its own BlockLayoutIndexConfig
        total_block_configs = len(pairs) * len(self.presentation_palette_ids) * len(self.CONFIG_NUMBERS)
        total_slide_configs = len(pairs) * len(self.presentation_palette_ids) * len(self.CONFIG_NUMBERS)
        
        sql_lines = [
            "-- INSERT statements for BlockLayoutIndexConfig and SlideLayoutIndexConfig tables",
            f"-- Processing {len(pairs)} slide/block layout pairs",
            f"-- BlockLayoutIndexConfig: one for each SlideLayoutIndexConfig record",
            f"-- SlideLayoutIndexConfig: {len(self.presentation_palette_ids)} palettes × {len(self.CONFIG_NUMBERS)} config numbers per pair",
            f"-- Total BlockLayoutIndexConfig records: {total_block_configs}",
            f"-- Total SlideLayoutIndexConfig records: {total_slide_configs}",
            ""
        ]

        total_block_inserts = 0
        total_slide_inserts = 0

        for pair_index, (slide_layout_id, block_layout_id) in enumerate(pairs):
            sql_lines.append(f"-- Pair {pair_index + 1}: {slide_layout_id} -> {block_layout_id}")
            
            # Insert into SlideLayoutIndexConfig for all combinations
            for i in range(len(self.presentation_palette_ids)):
                presentation_palette_id = self.presentation_palette_ids[i]
                block_layout_color_id = self.block_layout_config_ids[i]
                
                for config_number in self.CONFIG_NUMBERS:
                    # Create a BlockLayoutIndexConfig for this specific combination
                    index_color_id = self.INDEX_COLOR_IDS[config_number]
                    index_font_id = self.INDEX_FONT_IDS[config_number]
                    
                    block_uuid = self.generate_uuid7()
                    
                    sql_lines.extend([
                        f'INSERT INTO "BlockLayoutIndexConfig" (',
                        f'  "id",',
                        f'  "blockLayoutId",',
                        f'  "indexColorId",',
                        f'  "indexFontId"',
                        f')',
                        f'VALUES (',
                        f"  '{block_uuid}',",
                        f"  '{block_layout_id}',",
                        f'  {index_color_id},',
                        f'  {index_font_id}',
                        f');',
                        ""
                    ])
                    total_block_inserts += 1
                    
                    # Now create the corresponding SlideLayoutIndexConfig
                    slide_uuid = self.generate_uuid7()
                    total_slide_inserts += 1
                    
                    sql_lines.extend([
                        f'INSERT INTO "SlideLayoutIndexConfig" (',
                        f'  "id",',
                        f'  "presentationPaletteId",',
                        f'  "configNumber",',
                        f'  "slideLayoutId",',
                        f'  "blockLayoutIndexConfigId",',
                        f'  "blockLayoutConfigId"',
                        f')',
                        f'VALUES (',
                        f"  '{slide_uuid}',",
                        f"  '{presentation_palette_id}',",
                        f'  {config_number},',
                        f"  '{slide_layout_id}',",
                        f"  '{block_uuid}',",
                        f"  '{block_layout_color_id}'",
                        f');',
                        ""
                    ])
            
            sql_lines.append("")

        sql_lines.extend([
            f"-- Summary:",
            f"-- BlockLayoutIndexConfig inserts: {total_block_inserts}",
            f"-- SlideLayoutIndexConfig inserts: {total_slide_inserts}"
        ])
        
        return "\n".join(sql_lines)

    def save_sql_file(self, sql_content: str, output_dir: str = "output/standard_new/duo") -> str:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"slide_layout_insert_{timestamp}.sql"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        
        return filepath

    def process_csv_file(self, csv_file_path: str, output_dir: str = "output/standard_new/duo") -> str:
        print(f"Reading CSV file: {csv_file_path}")
        pairs = self.read_csv_data(csv_file_path)
        unique_block_count = len(set(block_id for _, block_id in pairs))
        
        print(f"Configuration:")
        print(f"  - Palettes: {len(self.presentation_palette_ids)}")
        print(f"  - Block layout color IDs: {len(self.block_layout_config_ids)}")
        print(f"  - Index color IDs: {self.INDEX_COLOR_IDS}")
        print(f"  - Index font IDs: {self.INDEX_FONT_IDS}")
        print(f"  - Config numbers: {self.CONFIG_NUMBERS}")
        print()
        print(f"CSV Data:")
        print(f"  - Total slide/block layout pairs: {len(pairs)}")
        print(f"  - Unique block layouts: {unique_block_count}")
        print()
        print(f"SQL Generation:")
        print(f"  - BlockLayoutIndexConfig records: {len(pairs) * len(self.presentation_palette_ids) * len(self.CONFIG_NUMBERS)}")
        print(f"  - SlideLayoutIndexConfig records: {len(pairs) * len(self.presentation_palette_ids) * len(self.CONFIG_NUMBERS)}")
        print(f"  - Total records: {(len(pairs) * len(self.presentation_palette_ids) * len(self.CONFIG_NUMBERS)) * 2}")
        
        # Show the pattern
        print(f"\nBlockLayoutIndexConfig Pattern (one per SlideLayoutIndexConfig):")
        for i, config_num in enumerate(self.CONFIG_NUMBERS):
            color_id = self.INDEX_COLOR_IDS[i]
            font_id = self.INDEX_FONT_IDS[i]
            print(f"  - Config {config_num}: uses color {color_id}, font {font_id}")
        
        sql_content = self.generate_complete_sql(pairs)
        filepath = self.save_sql_file(sql_content, output_dir)
        
        print(f"\nSQL file saved: {filepath}")
        return filepath


def main():
    generator = SlideLayoutSQLGenerator()
    
    csv_file = "csv/standard_new/duo/duo_icon_figure_color_index_345_font_index_0_slides_with_icon_blocks_and_outline_figures.csv"
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found")
        return
    
    try:
        generator.process_csv_file(csv_file)
        print("SQL generation completed successfully")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()