import csv
import time
import uuid
import ast

# --- UUIDv7 generator ---
def generate_uuid7() -> str:
    unix_ts_ms = int(time.time() * 1000)
    ts_bytes = unix_ts_ms.to_bytes(6, byteorder='big')
    random_bytes = uuid.uuid4().bytes[6:]
    uuid_bytes = ts_bytes + random_bytes
    uuid_bytes = bytearray(uuid_bytes)
    uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | (7 << 4)
    uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(uuid_bytes)))

def parse_pg_array(array_str):
    """Parse a Postgres curly-brace array string into a Python list of strings."""
    array_str = array_str.strip()
    if array_str.startswith("{") and array_str.endswith("}"):
        items = array_str[1:-1].split(",")
        return [item.strip().lower() for item in items if item.strip()]
    return []

def read_palette_mapping(path):
    """Read PresentationPalette CSV and return color -> palette_id mapping"""
    palette_map = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            color = row['color'].strip().lower()
            palette_id = row['id']
            palette_map[color] = palette_id
    return palette_map

def read_block_layout_mapping(path):
    """Read BlockLayoutConfig CSV and return config_id -> background_colors mapping (curly-brace arrays)."""
    block_configs = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            config_id = row['id']
            background_str = row['background'].strip()
            background_colors = parse_pg_array(background_str)
            block_configs.append({
                'id': config_id,
                'background_colors': background_colors,
                'raw_background': background_str
            })
    return block_configs

def find_matches(palette_map, block_configs):
    """Find matches between palette colors and block layout configs"""
    matches = []
    
    print(f"Looking for matches between {len(palette_map)} palette colors and {len(block_configs)} block configs...")
    
    for palette_color, palette_id in palette_map.items():
        print(f"\nSearching for palette color: {palette_color}")
        
        matching_configs = []
        for block_config in block_configs:
            if palette_color in block_config['background_colors']:
                matching_configs.append(block_config)
                print(f"  Found in config {block_config['id']}: {block_config['background_colors']}")
        
        if matching_configs:
            # If multiple configs match this palette color, create multiple matches
            for block_config in matching_configs:
                matches.append({
                    'id': generate_uuid7(),
                    'presentationPaletteId': palette_id,
                    'blockLayoutConfigId': block_config['id'],
                    'matched_background_color': palette_color,
                    'config_background_colors': str(block_config['background_colors'])
                })
        else:
            print(f"  No matching block config found for palette color: {palette_color}")
    
    return matches

def create_strategic_matches(palette_map, block_configs):
    """Create strategic matches - each palette color gets matched with each config that contains it"""
    matches = []
    
    # First, try exact matches
    exact_matches = find_matches(palette_map, block_configs)
    matches.extend(exact_matches)
    
    # If no exact matches found, create fallback matches
    if not exact_matches:
        print("\nNo exact matches found. Creating fallback matches...")
        
        palette_colors = list(palette_map.keys())
        
        for i, (palette_color, palette_id) in enumerate(palette_map.items()):
            # Use modulo to cycle through block configs
            block_config = block_configs[i % len(block_configs)]
            
            matches.append({
                'id': generate_uuid7(),
                'presentationPaletteId': palette_id,
                'blockLayoutConfigId': block_config['id'],
                'matched_background_color': palette_color,
                'config_background_colors': str(block_config['background_colors']),
                'match_type': 'fallback'
            })
            
            print(f"Created fallback match: {palette_color} -> {block_config['id']}")
    
    return matches

def main():
    # Fixed file paths - no parameters needed
    palette_file = 'presentation_palette_mapping.csv'
    block_file = 'block_layout_config_mapping.csv'
    output_file = 'slide_layout_index_config_mapping.csv'

    print(f"Reading palette mapping from: {palette_file}")
    palette_map = read_palette_mapping(palette_file)
    
    print(f"Reading block layout mapping from: {block_file}")
    block_configs = read_block_layout_mapping(block_file)
    
    print(f"\nFound {len(palette_map)} palette colors:")
    for color, palette_id in list(palette_map.items())[:5]:  # Show first 5
        print(f"  {color} -> {palette_id}")
    if len(palette_map) > 5:
        print(f"  ... and {len(palette_map) - 5} more")
    
    print(f"\nFound {len(block_configs)} block configs:")
    for config in block_configs[:3]:  # Show first 3
        print(f"  {config['id']}: {config['background_colors']}")
    if len(block_configs) > 3:
        print(f"  ... and {len(block_configs) - 3} more")
    
    # Always use strategic strategy
    matches = create_strategic_matches(palette_map, block_configs)
    
    # Write results
    fieldnames = ['id', 'presentationPaletteId', 'blockLayoutConfigId', 'matched_background_color', 'config_background_colors']
    if any('match_type' in match for match in matches):
        fieldnames.append('match_type')
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)
    
    print(f"\nWrote {len(matches)} matches to {output_file}")
    
    # Summary
    exact_count = sum(1 for m in matches if m.get('match_type') != 'fallback')
    fallback_count = sum(1 for m in matches if m.get('match_type') == 'fallback')
    
    if exact_count > 0:
        print(f"   {exact_count} exact matches based on background colors")
    if fallback_count > 0:
        print(f"   {fallback_count} fallback matches")

if __name__ == '__main__':
    main()