#!/usr/bin/env python3

import os
import csv
import uuid
import time
from datetime import datetime
from typing import List, Tuple, Dict


class FigureSQLGen:
    def __init__(self):
        # Arrays of indexes to loop through (similar to first script)
        self.INDEX_COLOR_IDS = [0, 1, 2]  # Multiple color indexes
        self.INDEX_FONT_IDS = [0, 0, 0]   # Multiple font indexes  
        self.CONFIG_NUMBERS = [0, 1, 2]   # Config numbers for SlideLayoutIndexConfig
        
        self.palette_ids = [
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
            '0197541e-5633-793c-a386-330466c622d8'

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
            '01975508-e5bd-7991-462c-50abb5fdc8e5'
        ]
        
        # Figure indexes for each config number (updated mapping)
        self.figure_indexes_by_config: Dict[int, Dict[str, int]] = {
0: {
  # outlines = 0
  "extraWideOutlineStdFive": 0,
  "iconCircleOutlineStd": 0,
  "iconSquareOutlineStd": 0,
  "infographicsOutlineStd": 0,
  "leftOutlineStdOne": 0,
  "outlinedCircleStd": 0,
  "outlineStdFour": 0,
  "outlineStdTwo": 0,
  "rectangleOutlineStdFour": 0,
  "rectangleOutlineStdSix": 0,
  "rectangleOutlineStdThree": 0,
  "squareOutlineStdEight": 0,
  "squareOutlineStdFour": 0,
  "squareOutlineStdFour.": 0,
  "squareOutlineStdThree": 0,
  "squareOutlineStdTwo": 0,
  "tallOutlineStdFour": 0,
  "wideOutlineStdEight": 0,
  "wideOutlineStdFive": 0,
  "wideOutlineStdFour": 0,
  "wideOutlineStdSix": 0,
  "wideOutlineStdTwo": 0,
  "wideOutlineStdThree": 0,

  # lines = 3
  "arcStdThree": 3,
  "axisStdEight": 3,
  "axisStdFour": 3,
  "axisStdSix": 3,
  "filledCircleStd": 3,
  "fourVerticalChevron": 3,
  "fourVerticalStepperStd": 3,
  "horizontalLineStd": 3,
  "rightArrowStd": 3,
  "ringStd": 3,
  "threeVerticalChevron": 3,
  "threeVerticalStepperStd": 3,
  "twoVerticalChevron": 3,
  "verticalLineStd": 3,

  # numbers = 9
  "numberFiveStd": 9,
  "numberFourStd": 9,
  "numberOneStd": 9,
  "numberSevenStd": 9,
  "numberSixStd": 9,
  "numberThreeStd": 9,
  "numberTwoStd": 9,
  "numberZeroEightStd": 9,
  "numberZeroFiveStd": 9,
  "numberZeroFourStd": 9,
  "numberZeroNineStd": 9,
  "numberZeroOneStd": 9,
  "numberZeroSevenStd": 9,
  "numberZeroSixStd": 9,
  "numberZeroThreeStd": 9,
  "numberZeroTwoStd": 9,
},

1: {
  # outlines = 1
  "extraWideOutlineStdFive": 1,
  "iconCircleOutlineStd": 1,
  "iconSquareOutlineStd": 1,
  "infographicsOutlineStd": 1,
  "leftOutlineStdOne": 1,
  "outlinedCircleStd": 1,
  "outlineStdFour": 1,
  "outlineStdTwo": 1,
  "rectangleOutlineStdFour": 1,
  "rectangleOutlineStdSix": 1,
  "rectangleOutlineStdThree": 1,
  "squareOutlineStdEight": 1,
  "squareOutlineStdFour": 1,
  "squareOutlineStdFour.": 1,
  "squareOutlineStdThree": 1,
  "squareOutlineStdTwo": 1,
  "tallOutlineStdFour": 1,
  "wideOutlineStdEight": 1,
  "wideOutlineStdFive": 1,
  "wideOutlineStdFour": 1,
  "wideOutlineStdSix": 1,
  "wideOutlineStdTwo": 1,
  "wideOutlineStdThree": 1,

  # lines = 4
  "arcStdThree": 4,
  "axisStdEight": 4,
  "axisStdFour": 4,
  "axisStdSix": 4,
  "filledCircleStd": 4,
  "fourVerticalChevron": 4,
  "fourVerticalStepperStd": 4,
  "horizontalLineStd": 4,
  "rightArrowStd": 4,
  "ringStd": 4,
  "threeVerticalChevron": 4,
  "threeVerticalStepperStd": 4,
  "twoVerticalChevron": 4,
  "verticalLineStd": 4,

  # numbers = 10
  "numberFiveStd": 10,
  "numberFourStd": 10,
  "numberOneStd": 10,
  "numberSevenStd": 10,
  "numberSixStd": 10,
  "numberThreeStd": 10,
  "numberTwoStd": 10,
  "numberZeroEightStd": 10,
  "numberZeroFiveStd": 10,
  "numberZeroFourStd": 10,
  "numberZeroNineStd": 10,
  "numberZeroOneStd": 10,
  "numberZeroSevenStd": 10,
  "numberZeroSixStd": 10,
  "numberZeroThreeStd": 10,
  "numberZeroTwoStd": 10,
},

2: {
  # outlines = 2
  "extraWideOutlineStdFive": 2,
  "iconCircleOutlineStd": 2,
  "iconSquareOutlineStd": 2,
  "infographicsOutlineStd": 2,
  "leftOutlineStdOne": 2,
  "outlinedCircleStd": 2,
  "outlineStdFour": 2,
  "outlineStdTwo": 2,
  "rectangleOutlineStdFour": 2,
  "rectangleOutlineStdSix": 2,
  "rectangleOutlineStdThree": 2,
  "squareOutlineStdEight": 2,
  "squareOutlineStdFour": 2,
  "squareOutlineStdFour.": 2,
  "squareOutlineStdThree": 2,
  "squareOutlineStdTwo": 2,
  "tallOutlineStdFour": 2,
  "wideOutlineStdEight": 2,
  "wideOutlineStdFive": 2,
  "wideOutlineStdFour": 2,
  "wideOutlineStdSix": 2,
  "wideOutlineStdTwo": 2,
  "wideOutlineStdThree": 2,
  
  # lines = 4
  "arcStdThree": 4,
  "axisStdEight": 4,
  "axisStdFour": 4,
  "axisStdSix": 4,
  "filledCircleStd": 4,
  "fourVerticalChevron": 4,
  "fourVerticalStepperStd": 4,
  "horizontalLineStd": 4,
  "rightArrowStd": 4,
  "ringStd": 4,
  "threeVerticalChevron": 4,
  "threeVerticalStepperStd": 4,
  "twoVerticalChevron": 4,
  "verticalLineStd": 4,

  # numbers = 11
  "numberFiveStd": 11,
  "numberFourStd": 11,
  "numberOneStd": 11,
  "numberSevenStd": 11,
  "numberSixStd": 11,
  "numberThreeStd": 11,
  "numberTwoStd": 11,
  "numberZeroEightStd": 11,
  "numberZeroFiveStd": 11,
  "numberZeroFourStd": 11,
  "numberZeroNineStd": 11,
  "numberZeroOneStd": 11,
  "numberZeroSevenStd": 11,
  "numberZeroSixStd": 11,
  "numberZeroThreeStd": 11,
  "numberZeroTwoStd": 11,
}}
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
        """Read name, blockLayoutId, slideLayoutId from CSV."""
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
        """Generate SQL with one BlockLayoutIndexConfig per SlideLayoutIndexConfig record."""
        # Create mappings
        name_to_blocks = {}  # figure_name -> set of block_ids
        block_to_name = {}   # block_id -> figure_name
        
        for name, block_id, slide_id in records:
            if name not in name_to_blocks:
                name_to_blocks[name] = set()
            name_to_blocks[name].add(block_id)
            block_to_name[block_id] = name
        
        # Calculate stats - now we need one BlockLayoutIndexConfig per SlideLayoutIndexConfig
        total_block_inserts = len(records) * len(self.palette_ids) * len(self.CONFIG_NUMBERS)
        total_slide_inserts = len(records) * len(self.palette_ids) * len(self.CONFIG_NUMBERS)
        
        sql_lines = [
            "-- INSERT statements for BlockLayoutIndexConfig and SlideLayoutIndexConfig tables",
            f"-- Processing {len(records)} figure/block/slide records",
            f"-- BlockLayoutIndexConfig: one for each SlideLayoutIndexConfig record",
            f"-- SlideLayoutIndexConfig: {len(self.palette_ids)} palettes × {len(self.CONFIG_NUMBERS)} config numbers per record",
            f"-- Total BlockLayoutIndexConfig records: {total_block_inserts}",
            f"-- Total SlideLayoutIndexConfig records: {total_slide_inserts}",
            "",
            "-- Figure Index Mapping by Config Number:",
        ]
        
        # Show figure mappings for each config number
        used_figures = sorted(name_to_blocks.keys())
        for config_num in self.CONFIG_NUMBERS:
            sql_lines.append(f"-- Config {config_num}:")
            for figure_name in used_figures:
                index = self.figure_indexes_by_config.get(config_num, {}).get(figure_name, 999)
                block_count = len(name_to_blocks[figure_name])
                sql_lines.append(f"--   {figure_name}: index {index} ({block_count} blocks)")
            sql_lines.append("")
        
        total_block_inserts_actual = 0
        total_slide_inserts_actual = 0

        # Generate records for each CSV record
        for record_index, (name, block_id, slide_id) in enumerate(records):
            sql_lines.append(f"-- Record {record_index + 1}: {name} -> {block_id} -> {slide_id}")
            
            for i in range(len(self.palette_ids)):
                palette_id = self.palette_ids[i]
                block_config_id = self.block_layout_config_ids[i]
                
                for config_number in self.CONFIG_NUMBERS:
                    # Get the config-specific index for this figure
                    config_index = self.figure_indexes_by_config.get(config_number, {}).get(name, 999)
                    
                    # Use the corresponding color/font combination for this config number
                    index_color_id = self.INDEX_COLOR_IDS[config_number]
                    index_font_id = self.INDEX_FONT_IDS[config_number]
                    
                    # Create a BlockLayoutIndexConfig for this specific combination
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
                        f"  '{block_id}',",
                        f'  {config_index},',  # Use config-specific index
                        f'  {index_font_id}',
                        f');',
                        ""
                    ])
                    total_block_inserts_actual += 1
                    
                    # Now create the corresponding SlideLayoutIndexConfig
                    slide_uuid = self.generate_uuid7()
                    total_slide_inserts_actual += 1
                    
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
                        f'  {config_number},',
                        f"  '{slide_id}',",
                        f"  '{block_uuid}',",
                        f"  '{block_config_id}'",
                        f');',
                        ""
                    ])
            
            sql_lines.append("")

        sql_lines.extend([
            f"-- Summary:",
            f"-- BlockLayoutIndexConfig inserts: {total_block_inserts_actual}",
            f"-- SlideLayoutIndexConfig inserts: {total_slide_inserts_actual}"
        ])
        
        return "\n".join(sql_lines)
    
    def save_sql(self, content: str, output_dir: str = "output/standard_new/duo") -> str:
        """Save SQL content to file."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"figure_layout_inserts_{timestamp}.sql"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def process(self, csv_path: str, output_dir: str = "output/standard_new/duo") -> str:
        """Main processing function."""
        print(f"Reading: {csv_path}")
        records = self.read_csv(csv_path)
        
        # Calculate stats
        unique_blocks = len(set(block_id for _, block_id, _ in records))
        unique_names = len(set(name for name, _, _ in records))
        unique_slides = len(set(slide_id for _, _, slide_id in records))
        
        block_inserts = unique_blocks * len(self.CONFIG_NUMBERS)
        slide_inserts = len(records) * len(self.palette_ids) * len(self.CONFIG_NUMBERS)
        total_inserts = block_inserts + slide_inserts
        
        print(f"Configuration:")
        print(f"  - Palettes: {len(self.palette_ids)}")
        print(f"  - Block layout config IDs: {len(self.block_layout_config_ids)}")
        print(f"  - Index color IDs: {self.INDEX_COLOR_IDS}")
        print(f"  - Index font IDs: {self.INDEX_FONT_IDS}")
        print(f"  - Config numbers: {self.CONFIG_NUMBERS}")
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
        
        # Show the pattern
        print(f"\nBlockLayoutIndexConfig Pattern:")
        for i, config_num in enumerate(self.CONFIG_NUMBERS):
            color_id = self.INDEX_COLOR_IDS[i]
            font_id = self.INDEX_FONT_IDS[i]
            print(f"  - Config {config_num}: uses color {color_id}, font {font_id}")
        
        # Check for unmapped figures in any config
        used_figures = set(name for name, _, _ in records)
        all_mapped_figures = set()
        for config_mapping in self.figure_indexes_by_config.values():
            all_mapped_figures.update(config_mapping.keys())
        
        unmapped = used_figures - all_mapped_figures
        if unmapped:
            print(f"\n⚠️ Unmapped figures (will use index 999): {sorted(unmapped)}")
        
        sql_content = self.generate_sql(records)
        filepath = self.save_sql(sql_content, output_dir)
        
        print(f"\nSQL file saved: {filepath}")
        return filepath


def main():
    gen = FigureSQLGen()
    
    csv_file = "csv/standard_new/duo/duo_figure_custom_indices_figure_blocks_with_outlines_-_no_change_needed-_no_change_needed.csv"
    
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