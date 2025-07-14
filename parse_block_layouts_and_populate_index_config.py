import os
import re
import json
import csv
import ast
from typing import Dict, List, Tuple, Optional
import glob
import uuid
import shutil

class BlockLayoutIndexConfigPopulator:
    def __init__(self, json_input_path: str, mapping_csv_path: str, slide_insertion_dir: str):
        self.json_input_path = json_input_path
        self.mapping_csv_path = mapping_csv_path
        self.slide_insertion_dir = slide_insertion_dir
        self.mapping_data = {}
        self.slides_from_sql = {}
        self.slides_from_json = {}
        
    def load_mapping_csv(self):
        """Load the block layout config mapping from CSV (if it exists)"""
        print(f"Loading mapping from: {self.mapping_csv_path}")
        
        if not os.path.exists(self.mapping_csv_path):
            print(f"Warning: Mapping CSV file not found at {self.mapping_csv_path}")
            print("Proceeding without mapping corrections...")
            return
        
        try:
            with open(self.mapping_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Check what columns are actually available
                if reader.fieldnames:
                    print(f"CSV columns found: {reader.fieldnames}")
                
                # Check if we have the expected columns
                expected_columns = ['block_type', 'extracted_color_index', 'extracted_font_index', 'correct_color_index', 'correct_font_index']
                missing_columns = [col for col in expected_columns if col not in reader.fieldnames]
                
                if missing_columns:
                    print(f"Warning: Missing expected columns in CSV: {missing_columns}")
                    print("Proceeding without mapping corrections...")
                    return
                
                for row in reader:
                    # Create a key from block_type, extracted_color_index, extracted_font_index
                    key = f"{row['block_type']}_{row['extracted_color_index']}_{row['extracted_font_index']}"
                    self.mapping_data[key] = {
                        'correct_color_index': int(row['correct_color_index']),
                        'correct_font_index': int(row['correct_font_index'])
                    }
            
            print(f"Loaded {len(self.mapping_data)} mapping entries")
            
        except Exception as e:
            print(f"Error loading CSV mapping: {e}")
            print("Proceeding without mapping corrections...")
    
    def parse_sql_files(self):
        """Parse SQL files to extract slide and block layout information"""
        print(f"Parsing SQL files from: {self.slide_insertion_dir}")
        
        # Find all SQL files in the directory
        sql_files = glob.glob(os.path.join(self.slide_insertion_dir, "**/*.sql"), recursive=True)
        print(f"Found {len(sql_files)} SQL files to process")
        
        for sql_file in sql_files:
            print(f"Processing: {os.path.basename(sql_file)}")
            
            with open(sql_file, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Debug: Show file structure
                self.debug_sql_structure(content, sql_file)
                
                # Extract slide layout information
                slide_layout = self.parse_slide_layout(content)
                if slide_layout:
                    slide_name = slide_layout['name']
                    slide_number = slide_layout['number']
                    
                    # Create key with both number and name (matching JSON format)
                    slide_key = f"{slide_number}_{slide_name}"
                    
                    self.slides_from_sql[slide_key] = {
                        'slideLayoutId': slide_layout['id'],
                        'slideNumber': slide_number,
                        'slideName': slide_name,
                        'blocks': self.parse_block_layouts(content)
                    }
                    print(f"  ✓ Found slide: {slide_key} with {len(self.slides_from_sql[slide_key]['blocks'])} blocks")
                else:
                    print(f"  ✗ Could not parse slide layout from {os.path.basename(sql_file)}")
        
        print(f"Found {len(self.slides_from_sql)} slides from SQL files")
        if self.slides_from_sql:
            print(f"SQL slide keys: {list(self.slides_from_sql.keys())}")
    
    def debug_sql_structure(self, content: str, file_path: str):
        """Debug SQL file structure to understand the format"""
        lines = content.split('\n')
        slide_layout_lines = []
        
        for i, line in enumerate(lines):
            if 'SlideLayout' in line or 'INSERT INTO' in line:
                slide_layout_lines.append(f"Line {i+1}: {line.strip()}")
        
        if slide_layout_lines:
            print(f"    SlideLayout-related lines in {os.path.basename(file_path)}:")
            for line in slide_layout_lines[:5]:  # Show first 5 relevant lines
                print(f"      {line}")
        else:
            print(f"    No SlideLayout lines found in {os.path.basename(file_path)}")
    
    def parse_slide_layout(self, content: str) -> Optional[Dict]:
        """Parse SlideLayout information from SQL content with multiple approaches"""
        print(f"    Parsing slide layout...")
        
        # Method 1: Look for complete INSERT INTO "SlideLayout" statement
        # This handles the multi-line format
        pattern1 = r'INSERT INTO "SlideLayout"\s*\([^)]+\)\s*VALUES\s*\(\s*\'([^\']+)\',\s*\'([^\']+)\',\s*(\d+)'
        match1 = re.search(pattern1, content, re.DOTALL)
        
        if match1:
            result = {
                'id': match1.group(1),
                'name': match1.group(2),
                'number': int(match1.group(3))
            }
            print(f"    ✓ Method 1 - Parsed slide: {result}")
            return result
        
        # Method 2: Look for just the VALUES section with quoted strings
        pattern2 = r'VALUES\s*\(\s*\'([a-f0-9-]+)\',\s*\'([^\']+)\',\s*(\d+)'
        match2 = re.search(pattern2, content, re.DOTALL)
        
        if match2:
            result = {
                'id': match2.group(1),
                'name': match2.group(2),
                'number': int(match2.group(3))
            }
            print(f"    ✓ Method 2 - Parsed slide: {result}")
            return result
        
        # Method 3: Find any line with UUID pattern followed by quoted name and number
        uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
        lines = content.split('\n')
        
        for line in lines:
            if re.search(uuid_pattern, line) and "'" in line:
                # Try to extract UUID, name, and number from this line
                uuid_match = re.search(f"'({uuid_pattern})'", line)
                if uuid_match:
                    uuid_val = uuid_match.group(1)
                    
                    # Look for the next quoted string (name)
                    remaining = line[uuid_match.end():]
                    name_match = re.search(r"'([^']+)'", remaining)
                    if name_match:
                        name_val = name_match.group(1)
                        
                        # Look for number after the name
                        remaining2 = remaining[name_match.end():]
                        number_match = re.search(r'(\d+)', remaining2)
                        if number_match:
                            number_val = int(number_match.group(1))
                            
                            result = {
                                'id': uuid_val,
                                'name': name_val,
                                'number': number_val
                            }
                            print(f"    ✓ Method 3 - Parsed slide: {result}")
                            return result
        
        print(f"    ✗ All parsing methods failed")
        
        # Show some content for debugging
        slide_lines = [line for line in content.split('\n') if 'SlideLayout' in line or 'VALUES' in line]
        if slide_lines:
            print(f"    Debug - SlideLayout/VALUES lines:")
            for line in slide_lines[:3]:
                print(f"      {line.strip()}")
        
        return None
    
    def parse_block_layouts(self, content: str) -> List[Dict]:
        """Parse BlockLayout entries from SQL content"""
        blocks = []
        
        # Look for BlockLayout INSERT with more flexible pattern
        patterns = [
            r'INSERT INTO "BlockLayout"[^V]*VALUES\s*(.*?)(?=RETURNING|\s*;)',
            r'-- Create BlockLayouts.*?VALUES\s*(.*?)(?=RETURNING|\s*;)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                values_section = match.group(1)
                
                # Parse each BlockLayout entry
                value_pattern = r"\('([^']+)',\s*'([^']+)',\s*'([^']+)'::[^)]*\)"
                
                for block_match in re.finditer(value_pattern, values_section):
                    block_id = block_match.group(1)
                    slide_layout_id = block_match.group(2)
                    block_type = block_match.group(3)
                    
                    blocks.append({
                        'blockLayoutId': block_id,
                        'slideLayoutId': slide_layout_id,
                        'blockLayoutType': block_type
                    })
                
                break  # Stop after first successful match
        
        return blocks
    
    def load_json_data(self):
        """Load slide configuration data from JSON file"""
        print(f"Loading slide configuration from: {self.json_input_path}")
        
        with open(self.json_input_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            # Process each slide
            for i, slide in enumerate(data):
                slide_layout_name = slide.get('slide_layout_name', '')
                slide_number = slide.get('slide_layout_number', 0)
                
                print(f"  Processing JSON slide {i}: layout_name='{slide_layout_name}', number={slide_number}")
                
                # Clean the slide layout name
                clean_name = self.clean_slide_layout_name(slide_layout_name)
                
                if clean_name:
                    # Create key with both number and name
                    slide_key = f"{slide_number}_{clean_name}"
                    
                    self.slides_from_json[slide_key] = {
                        'slideConfig': slide.get('slideConfig', {}),
                        'blocks': slide.get('blocks', []),
                        'slideNumber': slide_number,
                        'slideName': clean_name,
                        'sql_config': slide.get('sql_config', {})
                    }
                    print(f"    Added JSON slide: {slide_key}")
                else:
                    print(f"    WARNING: Clean name is empty for slide {i}")
        
        print(f"Loaded {len(self.slides_from_json)} slides from JSON")
        if self.slides_from_json:
            print(f"JSON slide keys (first 10): {list(self.slides_from_json.keys())[:10]}...")
    
    def clean_slide_layout_name(self, name: str) -> str:
        """Clean slide layout name by removing background and z-index info"""
        # Remove 'background_N z-index N' pattern
        cleaned = re.sub(r'\s*background_\d+\s*z-index\s*\d+\s*$', '', name, flags=re.IGNORECASE)
        result = cleaned.strip()
        return result
    
    def extract_color_and_font_indices(self, block_type: str, slide_config: Dict) -> Tuple[int, int]:
        """Extract color and font indices from slideConfig"""
        if not slide_config or block_type not in slide_config:
            print(f"        Warning: Block type '{block_type}' not found in slideConfig")
            return 0, 0
        
        block_config = slide_config[block_type]
        
        # Get the first background color as the primary color context
        background_colors = list(block_config.keys())
        if not background_colors:
            return 0, 0
        
        primary_bg_color = background_colors[0]
        color_font_combinations = block_config[primary_bg_color]
        
        if not color_font_combinations:
            return 0, 0
        
        # Use the first combination as the primary
        primary_combination = color_font_combinations[0]
        
        # Map colors to indices
        color_to_index = {
            '#2b2d33': 0,  # dark text
            '#808185': 1,  # gray text  
            '#5a82fa': 2,  # blue text
            '#ffffff': 3,  # white
            # Add more color mappings as needed
        }
        
        # Map fonts to indices
        font_to_index = {
            'arial': 0,
            'roboto': 1,
            'inter': 2,
            # Add more font mappings as needed
        }
        
        text_color = primary_combination.get('color', '#2b2d33')
        font_family = primary_combination.get('fontFamily', 'arial')
        
        color_index = color_to_index.get(text_color, 0)
        font_index = font_to_index.get(font_family, 0)
        
        print(f"        Extracted: color='{text_color}' -> {color_index}, font='{font_family}' -> {font_index}")
        return color_index, font_index
    
    def match_slides_and_generate_config(self):
        """Match slides between SQL and JSON, then generate BlockLayoutIndexConfig entries"""
        print("Matching slides and generating BlockLayoutIndexConfig entries...")
        
        print(f"SQL slides found: {len(self.slides_from_sql)}")
        print(f"JSON slides found: {len(self.slides_from_json)}")
        
        if not self.slides_from_sql:
            print("ERROR: No SQL slides found! Check SQL file parsing.")
            return []
        
        if not self.slides_from_json:
            print("ERROR: No JSON slides found! Check JSON file format.")
            return []
        
        index_config_entries = []
        matched_count = 0
        
        # Show some sample keys for debugging
        print(f"Sample SQL slide keys: {list(self.slides_from_sql.keys())[:3]}")
        print(f"Sample JSON slide keys: {list(self.slides_from_json.keys())[:3]}")
        
        for sql_slide_key, sql_data in self.slides_from_sql.items():
            print(f"  Looking for SQL slide: {sql_slide_key}")
            
            # Try to find matching JSON slide
            json_slide_data = self.slides_from_json.get(sql_slide_key)
            
            if json_slide_data:
                matched_count += 1
                print(f"  ✓ Matched slide: {sql_slide_key}")
                
                # Get slide configuration from JSON
                slide_config = json_slide_data['slideConfig']
                
                # Process each block in the SQL slide
                for sql_block in sql_data['blocks']:
                    block_id = sql_block['blockLayoutId']
                    block_type = sql_block['blockLayoutType']
                    
                    print(f"    Processing SQL block: {block_id} ({block_type})")
                    
                    # Extract color and font indices from slideConfig
                    color_index, font_index = self.extract_color_and_font_indices(block_type, slide_config)
                    
                    # Apply mapping corrections if available
                    corrected_color_index, corrected_font_index = self.apply_mapping_correction(
                        block_type, color_index, font_index
                    )
                    
                    index_config_entries.append({
                        'blockLayoutId': block_id,
                        'indexColorId': corrected_color_index,
                        'indexFontId': corrected_font_index
                    })
                    
                    print(f"      ✓ Added block {block_id} ({block_type}): color={color_index}->{corrected_color_index}, font={font_index}->{corrected_font_index}")
            else:
                print(f"  ✗ Warning: No matching JSON slide found for SQL slide: {sql_slide_key}")
                # Try to find partial matches
                partial_matches = [key for key in self.slides_from_json.keys() if sql_data['slideName'] in key]
                if partial_matches:
                    print(f"    Possible partial matches: {partial_matches[:3]}")
        
        print(f"Matched {matched_count} slides out of {len(self.slides_from_sql)} SQL slides")
        return index_config_entries
    
    def apply_mapping_correction(self, block_type: str, color_index: int, font_index: int) -> Tuple[int, int]:
        """Apply CSV mapping corrections to extracted indices"""
        if not self.mapping_data:
            return color_index, font_index
        
        key = f"{block_type}_{color_index}_{font_index}"
        
        if key in self.mapping_data:
            mapping = self.mapping_data[key]
            corrected_color = mapping['correct_color_index']
            corrected_font = mapping['correct_font_index']
            print(f"        Applied mapping correction for {key}: ({color_index},{font_index}) -> ({corrected_color},{corrected_font})")
            return corrected_color, corrected_font
        else:
            print(f"        No mapping found for {key}, using original indices")
            return color_index, font_index
    
    def generate_sql(self, index_config_entries):
        """Generate SQL INSERT statements"""
        if not index_config_entries:
            return "-- No BlockLayoutIndexConfig entries to generate"
        
        sql_lines = [
            "-- Generated BlockLayoutIndexConfig entries",
            "-- Based on slideConfig extraction and CSV mapping",
            "",
            'INSERT INTO "BlockLayoutIndexConfig" (',
            '    "id", "blockLayoutId", "indexColorId", "indexFontId"',
            ') VALUES'
        ]
        
        for i, entry in enumerate(index_config_entries):
            # Generate UUID for the new record
            record_id = str(uuid.uuid4())
            
            sql_line = f"    ('{record_id}', '{entry['blockLayoutId']}', {entry['indexColorId']}, {entry['indexFontId']})"
            if i < len(index_config_entries) - 1:
                sql_line += ","
            
            sql_lines.append(sql_line)
        
        sql_lines.extend([
            "RETURNING *;",
            "",
            f"-- Total: {len(index_config_entries)} entries"
        ])
        
        return "\n".join(sql_lines)
    
    def run(self):
        """Run the complete process, outputting per-slide BlockLayoutIndexConfig SQL files in color_insertion folders inside each group folder."""
        print("Starting BlockLayoutIndexConfig population process...")

        # Remove all existing color_insertion directories in each group
        for group_dir in os.listdir(self.slide_insertion_dir):
            group_path = os.path.join(self.slide_insertion_dir, group_dir)
            color_insertion_path = os.path.join(group_path, 'color_insertion')
            if os.path.isdir(color_insertion_path):
                print(f"Removing old color_insertion directory: {color_insertion_path}")
                shutil.rmtree(color_insertion_path)

        # Load mapping data (optional)
        self.load_mapping_csv()

        # Parse SQL files
        self.parse_sql_files()

        # Load JSON data
        self.load_json_data()

        # Match slides and generate config entries
        index_config_entries = self.match_slides_and_generate_config()

        # Build a mapping from blockLayoutId to slide key for grouping
        block_to_slide = {}
        for slide_key, sql_data in self.slides_from_sql.items():
            for block in sql_data['blocks']:
                block_to_slide[block['blockLayoutId']] = slide_key

        # Build a mapping from slide name prefix to group folder by matching *.sql files in slide_insertion subfolders
        slide_name_to_group = {}
        for group_dir in os.listdir(self.slide_insertion_dir):
            group_path = os.path.join(self.slide_insertion_dir, group_dir)
            slide_insertion_path = os.path.join(group_path, 'slide_insertion')
            if not os.path.isdir(slide_insertion_path):
                continue
            for fname in os.listdir(slide_insertion_path):
                if fname.endswith('.sql'):
                    base_name = fname[:-len('.sql')]
                    slide_name_to_group[base_name] = group_path

        # Group entries by slide key
        slide_entries = {}
        for entry in index_config_entries:
            block_id = entry['blockLayoutId']
            slide_key = block_to_slide.get(block_id, None)
            if slide_key is not None:
                if slide_key not in slide_entries:
                    slide_entries[slide_key] = []
                slide_entries[slide_key].append(entry)
            else:
                print(f"Warning: blockLayoutId {block_id} not found in any slide, skipping.")

        total_entries = 0
        for slide_key, entries in slide_entries.items():
            # Get slide name (not number)
            slide_name = self.slides_from_sql[slide_key]['slideName']
            # Find the group folder for this slide using prefix matching
            matched_group_folder = None
            for base_name, group_folder in slide_name_to_group.items():
                if base_name.startswith(slide_name):
                    matched_group_folder = group_folder
                    matched_base_name = base_name
                    break
            if not matched_group_folder:
                print(f"Warning: Could not find group folder for slide {slide_name} (key: {slide_key}), skipping.")
                continue
            color_insertion_dir = os.path.join(matched_group_folder, 'color_insertion')
            os.makedirs(color_insertion_dir, exist_ok=True)
            sql_output = self.generate_sql(entries)
            # Use just the matched base_name for the output filename
            safe_base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', matched_base_name)
            output_file = os.path.join(color_insertion_dir, f"{safe_base_name}.sql")
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write(sql_output)
            print(f"Generated SQL for slide {slide_name} saved to: {output_file}")
            total_entries += len(entries)

        print(f"Process completed. Generated {total_entries} BlockLayoutIndexConfig entries across {len(slide_entries)} slides.")

if __name__ == "__main__":
    # Configuration
    json_input_path = "my_output/sql_generator_input.json"
    mapping_csv_path = "block_layout_config_mapping.csv"  # Optional
    slide_insertion_dir = "my_sql_output"
    
    # Run the process
    populator = BlockLayoutIndexConfigPopulator(json_input_path, mapping_csv_path, slide_insertion_dir)
    populator.run()