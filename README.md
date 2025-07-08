# Figma to SQL Generator Workflow (Internal Tool)

## Overview
This internal tool automates the process of extracting design and content data from Figma and generating SQL files to populate your company's presentation database.  
It ensures that all slide layouts, blocks, styles, and related assets are consistently and safely transferred from design to production.

---

## Data Flow & Table Structure

### Main Tables Populated

- **SlideLayout**: Stores metadata for each slide layout (name, type, number, etc.).
- **BlockLayout**: Stores each block (text, image, figure, etc.) belonging to a slide.
- **BlockLayoutStyles**: Stores style information for each block (color, font, alignment, etc.).
- **BlockLayoutDimensions**: Stores position and size for each block.
- **Figure**: Stores figure-specific data (if present).
- **PrecompiledImage**: Stores references to precompiled images and their color variants.
- **SlideLayoutAdditionalInfo**: Stores extra metadata for slides (e.g., max symbols, headers).
- **SlideLayoutDimensions**: Stores overall slide dimensions.
- **SlideLayoutStyles**: Stores overall slide style settings.

All these tables are created and maintained in your company's presentation database.

---

## Full Workflow: Figma to Database

### 1. Extract Data from Figma
- **Script:** `figma.py`
- **What it does:** Connects to Figma, extracts all relevant slides and blocks, and outputs two JSON files:
  - `figma_extract.json`: Raw, detailed export from Figma.
  - `sql_generator_input.json`: Cleaned and normalized data ready for SQL generation.

### 2. Generate SQL Files
- **Script:** `slide_insertion.py`
- **What it does:** Reads the normalized JSON and generates SQL files for each slide, with all necessary `INSERT` statements for the tables above.
- **Modes:**
  - **Auto (Batch):** No user input, processes all slides in one go.
  - **Manual (Interactive):** Prompts for each block/slide, allowing custom overrides.

### 3. Validate SQL Queries
- **Script:** `sql_validator.py`
- **What it does:** Checks all generated SQL files for:
  - Syntax errors
  - Missing required fields
  - Referential integrity (e.g., block IDs match slide IDs)
- **Why:** Prevents corrupt or incomplete data from being loaded into the database.

### 4. Apply (Pollute) SQL to the Database
- **Script:** `sql_pollution.py`
- **What it does:** Executes the validated SQL files against your company's presentation database, populating all the tables above.
- **Order:** Ensures tables are populated in the correct order to maintain foreign key relationships.

### 5. Database Configuration (`database.ini`)
- **Purpose:** Stores all connection parameters for your internal database (host, port, user, password, database name, etc.).
- **Usage:** Both `sql_validator.py` and `sql_pollution.py` read this file for DB access.

---

## Example Workflow

```bash
# 1. Extract from Figma
py figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output

# 2. Generate SQL
py slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output

# 3. Validate SQL
py sql_validator.py --input-dir my_sql_output

# 4. Apply SQL to DB
py sql_pollution.py --input-dir my_sql_output --db-config database.ini
```

---

## Configuration File: `config.py`
- **Centralizes all settings** for the workflow.
- Stores Figma API credentials, default values, slide/block mappings, color and watermark settings, and logic for categorizing slides/blocks.
- **Ensures consistency** between extraction and SQL generation.

---

## Script Descriptions

### `figma.py`
- Extracts slides and blocks from Figma.
- Handles color, z-index, style, and block type extraction.
- Outputs JSON files for further processing.

### `slide_insertion.py`
- Reads the normalized JSON.
- Generates SQL for all relevant tables.
- Supports both auto and manual modes.

### `sql_validator.py`
- Validates SQL files for syntax, completeness, and referential integrity.

### `sql_pollution.py`
- Applies validated SQL to the database, handling all dependencies and order.

### `database.ini`
- Stores database connection settings in INI format.

---

## Русская версия

### Общий процесс: Figma → База данных

#### Основные таблицы

- **SlideLayout** — метаданные макета слайда
- **BlockLayout** — блоки (текст, изображение, фигура и т.д.)
- **BlockLayoutStyles** — стили блоков (цвет, шрифт, выравнивание)
- **BlockLayoutDimensions** — размеры и позиция блоков
- **Figure** — данные о фигурах
- **PrecompiledImage** — преподготовленные изображения и их варианты
- **SlideLayoutAdditionalInfo** — дополнительные параметры слайда
- **SlideLayoutDimensions** — размеры слайда
- **SlideLayoutStyles** — стили слайда

#### Полный рабочий процесс

1. **Извлечение из Figma:**  
   `figma.py` — экспортирует данные в JSON.

2. **Генерация SQL:**  
   `slide_insertion.py` — создает SQL-файлы для всех таблиц.

3. **Валидация SQL:**  
   `sql_validator.py` — проверяет синтаксис, обязательные поля и связи.

4. **Загрузка в БД:**  
   `sql_pollution.py` — применяет SQL к базе данных, соблюдая порядок.

5. **Конфиг базы данных:**  
   `database.ini` — параметры подключения к БД.

#### Пример команд

```bash
py figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output
py slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output
py sql_validator.py --input-dir my_sql_output
py sql_pollution.py --input-dir my_sql_output --db-config database.ini
```

---

## Конфигурационный файл: `config.py`
- Централизует все настройки для пайплайна.
- Хранит Figma API, значения по умолчанию, маппинги слайдов/блоков, цвета, вотермарки и логику категоризации.
- Гарантирует согласованность между извлечением и генерацией SQL.

---

## Описание скриптов

### `figma.py`
- Извлекает слайды и блоки из Figma.
- Обрабатывает цвета, z-index, стили и типы блоков.
- Выводит JSON для дальнейшей обработки.

### `slide_insertion.py`
- Читает нормализованный JSON.
- Генерирует SQL для всех таблиц.
- Поддерживает авто- и ручной режимы.

### `sql_validator.py`
- Валидирует SQL-файлы на синтаксис, полноту и связи.

### `sql_pollution.py`
- Применяет SQL к базе данных, учитывая все зависимости и порядок.

### `database.ini`
- Хранит параметры подключения к базе данных в формате INI. 