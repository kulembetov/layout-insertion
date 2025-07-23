import os
import re
import argparse
import shutil

# Table deletion order: child to parent
DELETE_ORDER = [
    "SlideLayoutIndexConfig",
    "BlockLayoutIndexConfig",
    "SlideLayoutStyles",
    "SlideLayoutDimensions",
    "SlideLayoutAdditionalInfo",
    "PrecompiledImage",
    "Figure",
    "BlockLayoutLimit",
    "BlockLayoutDimensions",
    "BlockLayoutStyles",
    "BlockLayout",
    "SlideLayout",
]

# Table to key column mapping
KEY_COLUMNS = {
    "SlideLayout": "id",
    "BlockLayout": "id",
    "BlockLayoutStyles": "blockLayoutId",
    "BlockLayoutDimensions": "blockLayoutId",
    "BlockLayoutLimit": "blockLayoutId",
    "Figure": "id",
    "PrecompiledImage": "id",
    "BlockLayoutIndexConfig": "id",
    "SlideLayoutIndexConfig": "id",
    "SlideLayoutStyles": "slideLayoutId",
    "SlideLayoutDimensions": "slideLayoutId",
    "SlideLayoutAdditionalInfo": "slideLayoutId",
}

# Extraction functions for each table


def extract_slide_layout_ids(sql):
    m = re.search(
        r"INSERT INTO \"SlideLayout\".*?VALUES\s*\(\s*'([^']+)'", sql, re.DOTALL
    )
    return [m.group(1)] if m else []


def extract_block_layout_ids(sql):
    m = re.search(r"INSERT INTO \"BlockLayout\".*?VALUES(.*?);", sql, re.DOTALL)
    if not m:
        return []
    values = m.group(1)
    # Each tuple: ('id', ...)
    return re.findall(r"\(\s*'([^']+)'", values)


def extract_block_layout_styles_ids(sql):
    m = re.search(r"INSERT INTO \"BlockLayoutStyles\".*?VALUES(.*?);", sql, re.DOTALL)
    if not m:
        return []
    values = m.group(1)
    # Each tuple: ('blockLayoutId', ...)
    return re.findall(r"\(\s*'([^']+)'", values)


def extract_block_layout_dimensions_ids(sql):
    m = re.search(
        r"INSERT INTO \"BlockLayoutDimensions\".*?VALUES(.*?);", sql, re.DOTALL
    )
    if not m:
        return []
    values = m.group(1)
    return re.findall(r"\(\s*'([^']+)'", values)


def extract_block_layout_limit_ids(sql):
    m = re.search(r"INSERT INTO \"BlockLayoutLimit\".*?VALUES(.*?);", sql, re.DOTALL)
    if not m:
        return []
    values = m.group(1)
    # Each tuple: (min_words, max_words, 'blockLayoutId')
    return re.findall(r"\(\s*[^,]+,\s*[^,]+,\s*'([^']+)'", values)


def extract_figure_ids(sql):
    m = re.search(r"INSERT INTO \"Figure\".*?VALUES(.*?);", sql, re.DOTALL)
    if not m:
        return []
    values = m.group(1)
    # Each tuple: ('id', ...)
    return re.findall(r"\(\s*'([^']+)'", values)


def extract_precompiled_image_ids(sql):
    m = re.search(r"INSERT INTO \"PrecompiledImage\".*?VALUES(.*?);", sql, re.DOTALL)
    if not m:
        return []
    values = m.group(1)
    # Each tuple: ('id', ...)
    return re.findall(r"\(\s*'([^']+)'", values)


def extract_block_layout_index_config_ids(sql):
    m = re.search(
        r"INSERT INTO \"BlockLayoutIndexConfig\".*?VALUES(.*?);", sql, re.DOTALL
    )
    if not m:
        return []
    values = m.group(1)
    return re.findall(r"\(\s*'([^']+)'", values)


def extract_slide_layout_index_config_ids(sql):
    m = re.search(
        r"INSERT INTO \"SlideLayoutIndexConfig\".*?VALUES(.*?);", sql, re.DOTALL
    )
    if not m:
        return []
    values = m.group(1)
    return re.findall(r"\(\s*'([^']+)'", values)


def extract_slide_layout_styles_ids(sql):
    m = re.search(
        r"INSERT INTO \"SlideLayoutStyles\".*?VALUES\s*\(\s*'([^']+)'", sql, re.DOTALL
    )
    return [m.group(1)] if m else []


def extract_slide_layout_dimensions_ids(sql):
    m = re.search(
        r"INSERT INTO \"SlideLayoutDimensions\".*?VALUES\s*\(\s*'([^']+)'",
        sql,
        re.DOTALL,
    )
    return [m.group(1)] if m else []


def extract_slide_layout_additional_info_ids(sql):
    m = re.search(
        r"INSERT INTO \"SlideLayoutAdditionalInfo\".*?VALUES\s*\(\s*'([^']+)'",
        sql,
        re.DOTALL,
    )
    return [m.group(1)] if m else []


EXTRACTORS = {
    "SlideLayout": extract_slide_layout_ids,
    "BlockLayout": extract_block_layout_ids,
    "BlockLayoutStyles": extract_block_layout_styles_ids,
    "BlockLayoutDimensions": extract_block_layout_dimensions_ids,
    "BlockLayoutLimit": extract_block_layout_limit_ids,
    "Figure": extract_figure_ids,
    "PrecompiledImage": extract_precompiled_image_ids,
    "BlockLayoutIndexConfig": extract_block_layout_index_config_ids,
    "SlideLayoutIndexConfig": extract_slide_layout_index_config_ids,
    "SlideLayoutStyles": extract_slide_layout_styles_ids,
    "SlideLayoutDimensions": extract_slide_layout_dimensions_ids,
    "SlideLayoutAdditionalInfo": extract_slide_layout_additional_info_ids,
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate SQL delete scripts for all slide groups in my_sql_output/. Traverses all subfolders and processes each slide_insertion folder."
    )
    parser.add_argument(
        "--root-dir",
        type=str,
        default="slide_deletion",
        help="Root directory to write deletion scripts (default: .)",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="my_sql_output",
        help="Input directory containing slide groups (default: my_sql_output)",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    root_dir = args.root_dir

    if not os.path.isdir(input_dir):
        print(f"Input directory '{input_dir}' does not exist.")
        return

    if not os.path.isdir(root_dir):
        print(f"Creating output directory '{root_dir}'...")
        os.makedirs(root_dir, exist_ok=True)

    print(f"Reading from: {input_dir}")
    print(f"Writing to: {root_dir}")

    for group in os.listdir(input_dir):
        group_path = os.path.join(input_dir, group)
        if not os.path.isdir(group_path):
            continue
        slide_insertion_dir = os.path.join(group_path, "slide_insertion")
        # Do NOT remove or modify the input slide_insertion_dir
        # Only remove the output slide_deletion directory if it exists
        output_group_path = os.path.join(root_dir, group)
        os.makedirs(output_group_path, exist_ok=True)
        slide_deletion_dir = os.path.join(output_group_path, "slide_deletion")
        if os.path.isdir(slide_deletion_dir):
            shutil.rmtree(slide_deletion_dir)
        os.makedirs(slide_deletion_dir, exist_ok=True)
        # If slide_insertion_dir does not exist, skip this group
        if not os.path.isdir(slide_insertion_dir):
            print(
                f"  Warning: {slide_insertion_dir} does not exist, skipping group {group}."
            )
            continue

        print(f"Processing group: {group}")
        for fname in os.listdir(slide_insertion_dir):
            if not fname.endswith(".sql"):
                continue
            print(f"  Processing: {fname}")
            with open(os.path.join(slide_insertion_dir, fname), encoding="utf-8") as f:
                sql = f.read()
            ids = {table: EXTRACTORS[table](sql) for table in DELETE_ORDER}
            out_path = os.path.join(slide_deletion_dir, fname)
            with open(out_path, "w", encoding="utf-8") as out:
                out.write("-- Generated delete statements for {}\n\n".format(fname))
                for table in DELETE_ORDER:
                    key_col = KEY_COLUMNS[table]
                    for id_ in ids[table]:
                        out.write(f"-- Delete from {table}\n")
                        out.write(
                            f'DELETE FROM "{table}" WHERE "{key_col}" = \'{id_}\';\n'
                        )
                out.write("\n")
        print(f"  Completed group: {group}")

    print(f"\nDeletion scripts generated in: {root_dir}")


if __name__ == "__main__":
    main()
