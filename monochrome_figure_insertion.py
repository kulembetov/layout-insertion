#!/usr/bin/env python3

import os
import csv
import uuid
import time
from datetime import datetime
from typing import List, Tuple, Dict


class FigureSQLGen:
    def __init__(self):
        self.INDEX_FONT_ID = 0
        
        self.palette_ids = [
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
        
        self.color_ids = [
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
        
        self.figure_indexes: Dict[str, int] = {
            "arcStdThree": 1,
            "axisStdEight": 1,
            "axisStdFour": 1,
            "axisStdSix": 1,
            "extraWideOutlineStdFive": 0,
            "filledCircleStd": 1,
            "fourVerticalChevron": 1,
            "fourVerticalStepperStd": 1,
            "horizontalLineStd": 1,
            "iconCircleOutlineStd": 0,
            "iconSquareOutlineStd": 0,
            "infographicsOutlineStd": 0,
            "leftOutlineStdOne": 0,
            "numberFiveStd": 2,
            "numberFourStd": 2,
            "numberOneStd": 2,
            "numberSevenStd": 2,
            "numberSixStd": 2,
            "numberThreeStd": 2,
            "numberTwoStd": 2,
            "numberZeroEightStd": 2,
            "numberZeroFiveStd": 2,
            "numberZeroFourStd": 2,
            "numberZeroNineStd": 2,
            "numberZeroOneStd": 2,
            "numberZeroSevenStd": 2,
            "numberZeroSixStd": 2,
            "numberZeroThreeStd": 2,
            "numberZeroTwoStd": 2,
            "outlinedCircleStd": 1,
            "outlineStdFour": 0,
            "outlineStdTwo": 0,
            "rectangleOutlineStdFour": 0,
            "rectangleOutlineStdSix": 0,
            "rectangleOutlineStdThree": 0,
            "rightArrowStd": 1,
            "ringStd": 1,
            "squareOutlineStdEight": 0,
            "squareOutlineStdFour": 0,
            "squareOutlineStdFour.": 0,
            "squareOutlineStdThree": 0,
            "squareOutlineStdTwo": 0,
            "tallOutlineStdFour": 0,
            "threeVerticalChevron": 1,
            "threeVerticalStepperStd": 1,
            "twoVerticalChevron": 1,
            "verticalLineStd": 1,
            "wideOutlineStdEight": 0,
            "wideOutlineStdFive": 0,
            "wideOutlineStdFour": 0,
            "wideOutlineStdSix": 0,
            "wideOutlineStdTwo": 0,
            "wideOutlineStdThree": 0,
        }

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

    def read_csv(self, path: str) -> List[Tuple[str, str, str]]:
        """Read name, blocklayoutid, slidelayoutid from CSV."""
        records = []
        try:
            with open(path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    name = row['name'].strip()
                    block_id = row['blocklayoutid'].strip()
                    slide_id = row['slidelayoutid'].strip()
                    records.append((name, block_id, slide_id))
            return records
        except Exception as e:
            raise Exception(f"Error reading CSV: {e}")
    
    def generate_sql(self, records: List[Tuple[str, str, str]]) -> str:
        """Generate SQL for both tables based on figure-specific indexes."""
        # Create mappings
        name_to_block = {}  # figure_name -> set of block_ids
        block_to_name = {}  # block_id -> figure_name
        block_layout_uuid_map: Dict[str, str] = {}
        
        for name, block_id, slide_id in records:
            if name not in name_to_block:
                name_to_block[name] = set()
            name_to_block[name].add(block_id)
            block_to_name[block_id] = name
        
        # Calculate stats
        unique_blocks = len(block_to_name)
        unique_names = len(name_to_block)
        total_slide_block_pairs = len(records)
        block_inserts = unique_blocks
        slide_inserts = total_slide_block_pairs * len(self.palette_ids)
        total_records = block_inserts + slide_inserts
        
        sql_lines = [
            "-- SUMMARY",
            f"-- Total records to insert: {total_records:,}",
            f"-- BlockLayoutIndexConfig: {block_inserts:,}",
            f"-- SlideLayoutIndexConfig: {slide_inserts:,}",
            f"-- Unique block layouts: {unique_blocks}",
            f"-- Unique figure names: {unique_names}",
            f"-- Slide/block pairs: {total_slide_block_pairs}",
            f"-- Palettes per pair: {len(self.palette_ids)}",
            "",
            "-- Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "",
            "-- Figure Index Mapping:",
        ]
        
        used_figures = sorted(name_to_block.keys())
        for figure_name in used_figures:
            index = self.figure_indexes.get(figure_name, 999)
            block_count = len(name_to_block[figure_name])
            sql_lines.append(f"-- {figure_name}: index {index} ({block_count} blocks)")
        
        sql_lines.extend([
            "",
            "-- BlockLayoutIndexConfig inserts",
            ""
        ])
        
        for figure_name in sorted(name_to_block.keys()):
            color_index = self.figure_indexes.get(figure_name, 999)
            blocks = sorted(name_to_block[figure_name])
            
            sql_lines.append(f"-- Figure: {figure_name} (index: {color_index})")
            for block_id in blocks:
                block_uuid = self.generate_uuid7()
                block_layout_uuid_map[block_id] = block_uuid
                
                sql_lines.extend([
                    f'INSERT INTO "BlockLayoutIndexConfig" (',
                    f'  "id",',
                    f'  "blockLayoutId",',
                    f'  "indexColorId",',
                    f'  "indexFontId"',
                    f')',
                    f'VALUES (',
                    f"  '{block_uuid}',",
                    f"  '{block_id}',",
                    f'  {color_index},',
                    f'  {self.INDEX_FONT_ID}',
                    f');',
                    ""
                ])
            sql_lines.append("")
        
        sql_lines.extend([
            "-- SlideLayoutIndexConfig inserts",
            ""
        ])
        
        pair_count = 0
        for name, block_id, slide_id in records:
            pair_count += 1
            sql_lines.append(f"-- Pair {pair_count}: {name} -> {slide_id}")
            
            block_uuid = block_layout_uuid_map[block_id]
            
            for i in range(len(self.palette_ids)):
                palette_id = self.palette_ids[i]
                color_id = self.color_ids[i]
                slide_uuid = self.generate_uuid7()
                
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
                    f"  '{palette_id}',",
                    f'  0,',
                    f"  '{slide_id}',",
                    f"  '{block_uuid}',",
                    f"  '{color_id}'",
                    f');',
                    ""
                ])
            sql_lines.append("")
        
        return "\n".join(sql_lines)
    
    def save_sql(self, content: str, output_dir: str = "output/standard_new/monochrome") -> str:
        """Save SQL content to file."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"figure_layout_inserts_{timestamp}.sql"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def process(self, csv_path: str, output_dir: str = "output/standard_new/monochrome") -> str:
        """Main processing function."""
        print(f"Reading: {csv_path}")
        records = self.read_csv(csv_path)
        
        # Calculate stats
        unique_blocks = len(set(block_id for _, block_id, _ in records))
        unique_names = len(set(name for name, _, _ in records))
        unique_slides = len(set(slide_id for _, _, slide_id in records))
        
        block_inserts = unique_blocks
        slide_inserts = len(records) * len(self.palette_ids)
        total_inserts = block_inserts + slide_inserts
        
        print(f"Configuration:")
        print(f"  - Palettes: {len(self.palette_ids)}")
        print(f"  - Color IDs: {len(self.color_ids)}")
        print()
        print(f"CSV Data:")
        print(f"  - Total records: {len(records):,}")
        print(f"  - Unique figures: {unique_names}")
        print(f"  - Unique blocks: {unique_blocks:,}")
        print(f"  - Unique slides: {unique_slides:,}")
        print()
        print(f"SQL Generation:")
        print(f"  - BlockLayoutIndexConfig records: {block_inserts:,}")
        print(f"  - SlideLayoutIndexConfig records: {slide_inserts:,}")
        print(f"  - Total records: {total_inserts:,}")
        
        used_figures = set(name for name, _, _ in records)
        unmapped = used_figures - set(self.figure_indexes.keys())
        if unmapped:
            print(f"\n⚠️ Unmapped figures (will use index 999): {sorted(unmapped)}")
        
        sql_content = self.generate_sql(records)
        filepath = self.save_sql(sql_content, output_dir)
        
        print(f"\nSQL file saved: {filepath}")
        return filepath


def main():
    gen = FigureSQLGen()
    
    csv_file = "csv/standard_new/monochrome/monochrome_figure_custom_indices.csv"
    
    if not os.path.exists(csv_file):
        print(f"Error: '{csv_file}' not found")
        return
    
    try:
        gen.process(csv_file)
        print("SQL generation completed successfully")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()