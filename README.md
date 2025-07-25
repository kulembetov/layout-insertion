# Project Structure

This repository is organized to support a full workflow from Figma design extraction to SQL generation and database population. Below is an overview of the main files and folders:

- `figma.py`: Extracts and normalizes data from Figma, outputs JSON files for further processing.
- `slide_insertion.py`: Reads normalized JSON and generates SQL files for each slide, handling all necessary tables.
- `sql_validator.py`: Validates generated SQL files for syntax and referential integrity before database insertion.
- `sql_pollution.py`: Executes validated SQL files against the target PostgreSQL database.
- `slide_deletion.py`: Handles deletion of slides, blocks, and images from the database, supporting selective and batch operations.
- `insert_palette.py`, `insert_block_layout_config.py`, `match_block_layout_presentation_palette.py`: Scripts for managing palette and block layout configuration, including mapping and matching between Figma and database structures.
- `color_config.py`, `color_pipeline.py`: Utilities for color extraction, normalization, and pipeline processing.
- `duo_color_insertion.py`, `duo_figure_insertion.py`, `monochrome_color_insertion.py`, `monochrome_figure_insertion.py`: Scripts for handling color and figure insertions for different presentation styles.
- `clean.py`, `clean_sql_timestamp.py`: Utility scripts for cleaning up data or timestamps.
- `config.py`: Central configuration file for all scripts, storing Figma API credentials, mappings, and default values.
- `database.ini`: Stores database connection parameters for PostgreSQL.
- `schema.prisma`: Prisma schema file for Node.js backend integration.
- `my_output/`, `my_sql_output/`: Output directories for extracted JSON and generated SQL files, respectively.
- `slide_deletion/`: Contains SQL files and scripts for deleting slides/blocks, organized by layout type (e.g., 1cols, 2cols, etc.).

---

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

**Windows:**
```bash
# 1. Extract from Figma
python figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output 

# 2. Insert into PresentationPalette
# manual mode
python insert_palette.py --json my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# auto mode
python insert_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 4. Match BlockLayoutConfig with PresentationPalette
python match_block_layout_presentation_palette.py

# 5. Generate SQL
python slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Validate SQL
python sql_validator.py --input-dir script/my_sql_output

# 7. Apply SQL to DB
python sql_pollution.py

# 8. Delete from the DB (blocks, slides, images)
python slide_deletion.py
```

**macOS:**
```bash
# 1. Extract from Figma
python3 figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output 

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
python3 match_block_layout_presentation_palette.py

# 5. Generate SQL
python3 slide_insertion.py --auto-from-figma script/my_output/sql_generator_input.json --output-dir script/my_sql_output

# 6. Validate SQL
python3 sql_validator.py --input-dir script/my_sql_output

# 7. Apply SQL to DB
python3 sql_pollution.py

# 8. Delete from the DB (blocks, slides, images)
python3 slide_deletion.py
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

### `slide_deletion.py`
- Deletes slides, blocks, and images from the database.
- Supports selective deletion based on slide numbers or block types.
- Useful for cleaning up test data or removing outdated content.

### `migrate_images.py`
- **Purpose:** Migrates images from Google Drive to Yandex Cloud Object Storage
- **Functionality:** 
  - Downloads images from a specified Google Drive folder
  - Uploads them to Yandex Cloud S3-compatible storage
  - Supports various image formats (JPG, PNG, GIF, BMP, WebP, TIFF, SVG)
  - Handles OAuth authentication with Google Drive API
  - Uses S3-compatible interface for Yandex Cloud storage
- **Configuration:** 
  - Requires `.env` file with Yandex Cloud credentials and Google Drive folder ID
  - Requires `credentials.json` file from Google Cloud Console for Google Drive API access
- **Dependencies:** `boto3`, `google-api-python-client`, `google-auth-oauthlib`, `python-dotenv`
- **Usage:** Run the script to migrate all images from Google Drive to Yandex Cloud storage

---

# Структура проекта

Репозиторий организован для поддержки полного цикла: от извлечения данных из Figma до генерации SQL и наполнения базы данных. Вот краткое описание основных файлов и папок:

- `figma.py`: Извлекает и нормализует данные из Figma, формирует JSON для дальнейшей обработки.
- `slide_insertion.py`: Читает нормализованный JSON и генерирует SQL-файлы для каждого слайда, формируя все необходимые таблицы.
- `sql_validator.py`: Валидирует сгенерированные SQL-файлы на синтаксис и целостность связей перед загрузкой в базу.
- `sql_pollution.py`: Выполняет валидированные SQL-файлы в целевой базе PostgreSQL.
- `slide_deletion.py`: Удаляет слайды, блоки и изображения из базы, поддерживает выборочное и пакетное удаление.
- `insert_palette.py`, `insert_block_layout_config.py`, `match_block_layout_presentation_palette.py`: Скрипты для управления палитрами и конфигурацией блоков, включая сопоставление между Figma и структурой базы.
- `color_config.py`, `color_pipeline.py`: Утилиты для извлечения, нормализации и обработки цветов.
- `duo_color_insertion.py`, `duo_figure_insertion.py`, `monochrome_color_insertion.py`, `monochrome_figure_insertion.py`: Скрипты для работы с цветами и фигурами для разных стилей презентаций.
- `clean.py`, `clean_sql_timestamp.py`: Вспомогательные скрипты для очистки данных или временных меток.
- `config.py`: Центральный конфиг для всех скриптов, хранит параметры Figma API, маппинги и значения по умолчанию.
- `database.ini`: Параметры подключения к PostgreSQL.
- `schema.prisma`: Файл схемы Prisma для интеграции с Node.js backend.
- `my_output/`, `my_sql_output/`: Папки для вывода извлечённых JSON и сгенерированных SQL-файлов соответственно.
- `slide_deletion/`: Содержит SQL-файлы и скрипты для удаления слайдов/блоков, организованные по типу макета (например, 1cols, 2cols и т.д.).

---

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

**Windows:**
```bash
# 1. Вставка в PresentationPalette
# ручной режим
python insert_palette.py --json script/my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# авто режим
python insert_palette.py --json script/my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 2. Вставка в BlockLayoutConfig
# ручной режим
python insert_block_layout_config.py --json script/my_output/sql_generator_input.json --mode manual
# авто режим
python insert_block_layout_config.py --json script/my_output/sql_generator_input.json --mode auto --db database.ini

# 3. Сопоставление BlockLayoutConfig с PresentationPalette
python match_block_layout_presentation_palette.py

# 4. Извлечение из Figma
python figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir script/my_output

# 5. Генерация SQL
python slide_insertion.py --auto-from-figma script/my_output/sql_generator_input.json --output-dir script/my_sql_output

# 6. Валидация SQL
python sql_validator.py --input-dir script/my_sql_output

# 7. Загрузка SQL в БД
python sql_pollution.py

# 8. Удаление из БД (блоков, слайдов, изображений)
python slide_deletion.py
```

**macOS:**
```bash
# 1. Вставка в PresentationPalette
# ручной режим
python3 insert_palette.py --json script/my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# авто режим
python3 insert_palette.py --json script/my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 2. Вставка в BlockLayoutConfig
# ручной режим
python3 insert_block_layout_config.py --json script/my_output/sql_generator_input.json --mode manual
# авто режим
python3 insert_block_layout_config.py --json script/my_output/sql_generator_input.json --mode auto --db database.ini

# 3. Сопоставление BlockLayoutConfig с PresentationPalette
python3 match_block_layout_presentation_palette.py

# 4. Извлечение из Figma
python3 figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir script/my_output

# 5. Генерация SQL
python3 slide_insertion.py --auto-from-figma script/my_output/sql_generator_input.json --output-dir script/my_sql_output

# 6. Валидация SQL
python3 sql_validator.py --input-dir script/my_sql_output

# 7. Загрузка SQL в БД
python3 sql_pollution.py

# 8. Удаление из БД (блоков, слайдов, изображений)
python3 slide_deletion.py
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

### `slide_deletion.py`
- Удаляет слайды, блоки и изображения из базы данных.
- Поддерживает выборочное удаление по номерам слайдов или типам блоков.
- Полезен для очистки тестовых данных или удаления устаревшего контента.

### `migrate_images.py`
- **Назначение:** Мигрирует изображения из Google Drive в Yandex Cloud Object Storage
- **Функциональность:** 
  - Скачивает изображения из указанной папки Google Drive
  - Загружает их в S3-совместимое хранилище Yandex Cloud
  - Поддерживает различные форматы изображений (JPG, PNG, GIF, BMP, WebP, TIFF, SVG)
  - Обрабатывает OAuth аутентификацию с Google Drive API
  - Использует S3-совместимый интерфейс для хранилища Yandex Cloud
- **Конфигурация:** 
  - Требует файл `.env` с учетными данными Yandex Cloud и ID папки Google Drive
  - Требует файл `credentials.json` из Google Cloud Console для доступа к Google Drive API
- **Зависимости:** `boto3`, `google-api-python-client`, `google-auth-oauthlib`, `python-dotenv`
- **Использование:** Запустите скрипт для миграции всех изображений из Google Drive в хранилище Yandex Cloud 