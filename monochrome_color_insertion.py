#!/usr/bin/env python3

import os
import csv
import uuid
import time
from datetime import datetime
from typing import List, Tuple, Dict


class SlideLayoutSQLGenerator:
    def __init__(self):
        # Configure this value as needed for indexColorId
        self.INDEX_COLOR_ID = 0
        self.INDEX_FONT_ID = 0
        
        self.presentation_palette_ids = [
            '01972f2f-2720-7e70-979f-67897512751c',
            '01972f33-713b-78c8-a85b-16be7f554e80',
            '01972f33-714e-79d0-839b-15d93f6f93d3',
            '01972f33-715c-72cc-bf14-e3822eab38ff',
            '01972f33-7170-7860-a83b-a9ac0505fd2c',
            '01972f33-6d95-78dc-9b16-ff56f646a49f',
            '01972f33-6d9e-75c4-b46a-fa4cd5535934',
            '01972f33-6da9-772c-b276-ec8286599769',
            '01972f33-6dd1-75b8-937d-a4ab048cadd5',
            '01972f33-6ddc-76d8-93d3-b2d228b2be61',
            '01972f33-6de8-7d64-9229-3dea33b70f1e',
            '01972f33-6df2-7668-9477-fa12dae2ee63',
            '01972f33-6dfe-77b0-b6a1-d2438fa4e366',
            '01972f33-6e07-757c-99a8-20b9d2b87fe4',
            '01972f33-6e10-7d58-b692-2e21ecfd4870',
            '01972f33-6e1b-7534-82d5-f006a866cfb7',
            '01972f33-6e2f-7dd4-b55d-cd4de5accf89',
            '01972f33-6e38-76e4-a3cf-69d392d907c3',
            '01972f33-6e41-79e8-8e78-9f5bb77435b2',
            '01972f33-6e4a-7e38-8e24-b79b35473f12'

        ]
        
        self.block_layout_color_ids = [
            '01972f48-c926-7ec0-9606-1b449b75c289',
            '01972f48-c933-7be4-ac68-f7f3cce76a42',
            '01972f4b-4c5c-78dc-a796-79dae3c2cc75',
            '01972f4b-4c82-73a8-a087-1e8c74208207',
            '01972f4e-b727-70d4-9bf5-59f57624c7c8',
            '01972f4e-b730-7758-8bb7-1a5136321988',
            '01972f50-a71f-7e70-8696-9401bfaf63d8',
            '01972f50-a728-70a0-9edd-82d3de8918b1',
            '01972f51-fb41-7f0c-946f-7c407a94483c',
            '01972f51-fb4a-7830-ac42-1800f4ed43c1',
            '01972f53-cbd9-7378-9da1-e47457266c71',
            '01972f53-cbe3-71c8-8b4e-2c97b024d66f',
            '01972f56-893c-71c8-99e1-94095d8ad23b',
            '01972f56-8948-77bc-8a50-7420c29671bf',
            '01972f58-e7cc-7ed4-b647-3d845aca5ef0',
            '01972f58-e7c1-729c-a976-bc48aebc8890',
            '01972f5a-8741-77a0-97ff-e03cb74df1ac',
            '01972f5a-8b35-7a40-8e7c-df0fc249f251',
            '01972f5b-b9b4-783c-87ff-5b5a9e23d85f',
            '01972f5b-b9bb-7558-a6db-17cbcc7f0a1f'
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
        sql_lines = [
            "-- INSERT statements for BlockLayoutIndexConfig and SlideLayoutIndexConfig tables",
            f"-- Processing {len(pairs)} slide/block layout pairs",
            f"-- Each block gets: 1 BlockLayoutIndexConfig + {len(self.presentation_palette_ids)} SlideLayoutIndexConfig records",
            ""
        ]

        processed_block_layouts = set()
        block_layout_uuid_map: Dict[str, str] = {}
        total_block_inserts = 0
        total_slide_inserts = 0

        for pair_index, (slide_layout_id, block_layout_id) in enumerate(pairs):
            sql_lines.append(f"-- Pair {pair_index + 1}: {slide_layout_id} -> {block_layout_id}")
            
            # Insert into BlockLayoutIndexConfig if not already processed
            if block_layout_id not in processed_block_layouts:
                block_uuid = self.generate_uuid7()
                block_layout_uuid_map[block_layout_id] = block_uuid
                
                sql_lines.extend([
                    f'INSERT INTO "BlockLayoutIndexConfig" (',
                    f'  "id",',
                    f'  "blockLayoutId",',
                    f'  "indexColorId"',
                    f'  "indexFontId"',
                    f')',
                    f'VALUES (',
                    f"  '{block_uuid}',",
                    f"  '{block_layout_id}',",
                    f'  {self.INDEX_COLOR_ID}',
                    f'  {self.INDEX_FONT_ID}',
                    f');',
                    ""
                ])
                processed_block_layouts.add(block_layout_id)
                total_block_inserts += 1
            
            # Use the stored UUID for this block layout
            block_uuid = block_layout_uuid_map[block_layout_id]
            
            # Insert into SlideLayoutIndexConfig for all palette/color combinations
            for i in range(len(self.presentation_palette_ids)):
                presentation_palette_id = self.presentation_palette_ids[i]
                block_layout_color_id = self.block_layout_color_ids[i]
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
                    f'  0,',
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

    def save_sql_file(self, sql_content: str, output_dir: str = "output/standard_new/monochrome") -> str:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"slide_layout_insert_{timestamp}.sql"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        
        return filepath

    def process_csv_file(self, csv_file_path: str, output_dir: str = "output/standard_new/monochrome") -> str:
        print(f"Reading CSV file: {csv_file_path}")
        pairs = self.read_csv_data(csv_file_path)
        unique_block_count = len(set(block_id for _, block_id in pairs))
        
        print(f"Configuration:")
        print(f"  - Palettes: {len(self.presentation_palette_ids)}")
        print(f"  - Block layout color IDs: {len(self.block_layout_color_ids)}")
        print(f"  - Index color ID: {self.INDEX_COLOR_ID}")
        print()
        print(f"CSV Data:")
        print(f"  - Total slide/block layout pairs: {len(pairs)}")
        print(f"  - Unique block layouts: {unique_block_count}")
        print()
        print(f"SQL Generation:")
        print(f"  - BlockLayoutIndexConfig records: {unique_block_count}")
        print(f"  - SlideLayoutIndexConfig records: {len(pairs) * len(self.presentation_palette_ids)}")
        print(f"  - Total records: {unique_block_count + (len(pairs) * len(self.presentation_palette_ids))}")
        
        sql_content = self.generate_complete_sql(pairs)
        filepath = self.save_sql_file(sql_content, output_dir)
        
        print(f"\nSQL file saved: {filepath}")
        return filepath


def main():
    generator = SlideLayoutSQLGenerator()
    
    csv_file = "csv/standard_new/monochrome/monochrome_icon_color_index_0_font_index_0.csv"
    
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