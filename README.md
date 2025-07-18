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

# 2. Insert into PresentationPalette
# manual mode
python insert_palette.py --json my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# auto mode
python insert_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 3. Insert into BlockLayoutConfig
# manual mode
python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode manual
# auto mode
python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini

# 4. Match BlockLayoutConfig with PresentationPalette
python match_block_layout_presentation_palette.py

# 5. Generate SQL
py slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Validate SQL
py sql_validator.py --input-dir my_sql_output

# 7. Apply SQL to DB
py sql_pollution.py

# 8. Delete from the DB (blocks, slides, images)
python slide_deletion.py
```
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

# Русская версия

## Обзор
Этот внутренний инструмент автоматизирует процесс извлечения данных из Figma и генерации SQL-файлов для заполнения корпоративной базы презентаций.
Он обеспечивает согласованную и безопасную передачу макетов слайдов, блоков, стилей и связанных ресурсов из дизайна в продакшн.

---

## Поток данных и структура таблиц

### Основные таблицы

- **SlideLayout**: метаданные макета слайда (имя, тип, номер и т.д.)
- **BlockLayout**: каждый блок (текст, изображение, фигура и т.д.), принадлежащий слайду
- **BlockLayoutStyles**: стили для каждого блока (цвет, шрифт, выравнивание и т.д.)
- **BlockLayoutDimensions**: позиция и размер каждого блока
- **Figure**: данные о фигурах (если есть)
- **PrecompiledImage**: ссылки на преподготовленные изображения и их цветовые варианты
- **SlideLayoutAdditionalInfo**: дополнительные метаданные слайда (максимум символов, заголовки и т.д.)
- **SlideLayoutDimensions**: размеры слайда
- **SlideLayoutStyles**: стили слайда

Все эти таблицы создаются и поддерживаются в корпоративной базе презентаций.

---

## Полный рабочий процесс: Figma → База данных

### 1. Извлечение данных из Figma
- **Скрипт:** `figma.py`
- **Что делает:** Подключается к Figma, извлекает все нужные слайды и блоки, создает два JSON-файла:
  - `figma_extract.json`: сырые, подробные данные из Figma
  - `sql_generator_input.json`: очищенные и нормализованные данные для генерации SQL

### 2. Генерация SQL-файлов
- **Скрипт:** `slide_insertion.py`
- **Что делает:** Читает нормализованный JSON и генерирует SQL-файлы для каждого слайда со всеми нужными `INSERT` для таблиц выше.
- **Режимы:**
  - **Авто (batch):** Без ввода пользователя, обрабатывает все слайды сразу
  - **Ручной (interactive):** Запрашивает параметры для каждого блока/слайда, позволяет переопределять значения

### 3. Валидация SQL-запросов
- **Скрипт:** `sql_validator.py`
- **Что делает:** Проверяет все сгенерированные SQL-файлы на:
  - Синтаксические ошибки
  - Отсутствие обязательных полей
  - Целостность связей (например, ID блоков и слайдов)
- **Зачем:** Предотвращает загрузку некорректных или неполных данных в базу

### 4. Загрузка SQL в базу данных
- **Скрипт:** `sql_pollution.py`
- **Что делает:** Выполняет валидированные SQL-файлы в корпоративной базе, заполняя все таблицы выше
- **Порядок:** Гарантирует правильную последовательность для поддержания связей

### 5. Конфиг базы данных (`database.ini`)
- **Назначение:** Хранит параметры подключения к БД (host, port, user, password, database name и т.д.)
- **Используется:** `sql_validator.py` и `sql_pollution.py` читают этот файл для доступа к БД

---

## Пример рабочего процесса

```bash
# 1. Вставка в PresentationPalette
# ручной режим
python insert_palette.py --json my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# авто режим
python insert_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 2. Вставка в BlockLayoutConfig
# ручной режим
python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode manual
# авто режим
python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini

# 3. Сопоставление BlockLayoutConfig с PresentationPalette
python match_block_layout_presentation_palette.py

# 4. Извлечение из Figma
py figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output

# 5. Генерация SQL
py slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Валидация SQL
py sql_validator.py --input-dir my_sql_output

# 7. Загрузка SQL в БД
py sql_pollution.py

# 8. Удаление из БД (блоков, слайдов, изображений)
python slide_deletion.py
```

---

## Конфигурационный файл: `config.py`
- Централизует все настройки для пайплайна
- Хранит Figma API, значения по умолчанию, маппинги слайдов/блоков, цвета, вотермарки и логику категоризации
- Гарантирует согласованность между извлечением и генерацией SQL

---

## Описание скриптов

### `figma.py`
- Извлекает слайды и блоки из Figma
- Обрабатывает цвета, z-index, стили и типы блоков
- Выводит JSON для дальнейшей обработки

### `slide_insertion.py`
- Читает нормализованный JSON
- Генерирует SQL для всех таблиц
- Поддерживает авто- и ручной режимы

### `sql_validator.py`
- Валидирует SQL-файлы на синтаксис, полноту и связи

### `sql_pollution.py`
- Применяет SQL к базе данных, учитывая все зависимости и порядок

### `database.ini`
- Хранит параметры подключения к базе данных в формате INI 