# Project Structure

This repository is organized to support a full workflow from Figma design extraction to SQL generation and database population. Below is an overview of the main files and folders:

- `figma.py`: Extracts and normalizes data from Figma, outputs JSON files for further processing.
- `slide_insertion.py`: Reads normalized JSON and generates SQL files for each slide, handling all necessary tables.
- `sql_validator.py`: Validates generated SQL files for syntax and referential integrity before database insertion.
- `sql_pollution.py`: Executes validated SQL files against the target PostgreSQL database.
- `slide_deletion.py`: Handles deletion of slides, blocks, and images from the database, supporting selective and batch operations.
- `account_creation.py`: Creates user accounts with authentication, subscriptions, payments, and AB testing groups in the database.
- `insert_presentation_palette.py`, `insert_block_layout_config.py`, `match_block_layout_presentation_palette.py`: Scripts for managing palette and block layout configuration, including mapping and matching between Figma and database structures.
- `config.py`: Central configuration file for all scripts, storing Figma API credentials, mappings, and default values.
- `database.ini`: Stores database connection parameters for PostgreSQL.
- `schema.prisma`: Prisma schema file for Node.js backend integration.
- `pyproject.toml`: Poetry configuration file for dependency management and project metadata.
- `.pre-commit-config.yaml`: Pre-commit hooks configuration for automated code quality checks.
- `my_output/`, `my_sql_output/`: Output directories for extracted JSON and generated SQL files, respectively.
- `slide_deletion/`: Contains SQL files and scripts for deleting slides/blocks, organized by layout type (e.g., 1cols, 2cols, etc.).

---

# Poetry Dependency Management

## Overview
This project uses Poetry for dependency management, providing a more robust and modern approach to handling Python dependencies compared to traditional `requirements.txt` files.

## What is Poetry?
Poetry is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and will manage (install/update) them for you.

## Installation

### 1. Install Poetry
```bash
# Install Poetry globally
curl -sSL https://install.python-poetry.org | python3 -

# Or using pip
pip install poetry
```

### 2. Install project dependencies
```bash
# Install all dependencies
poetry install

# Install only production dependencies
poetry install --no-dev
```

### 3. Activate virtual environment
```bash
# Activate the Poetry shell
poetry shell

# Or run commands directly with poetry run
poetry run python figma.py --help
```

## Usage

### Adding new dependencies
```bash
# Add a production dependency
poetry add requests

# Add a development dependency
poetry add --group dev pytest

# Add with specific version
poetry add pandas==2.3.1
```

### Updating dependencies
```bash
# Update all dependencies
poetry update

# Update specific dependency
poetry update pandas
```

### Running scripts
```bash
# Run scripts within Poetry environment
poetry run python figma.py --help

# Or activate shell first
poetry shell
python figma.py --help
```

### Managing virtual environment
```bash
# Show virtual environment info
poetry env info

# Remove virtual environment
poetry env remove python

# Create new virtual environment
poetry env use python3.13
```

## Configuration

The project uses `pyproject.toml` for configuration with:
- **Package mode disabled**: This is a script-based project, not a Python package
- **Python 3.13+**: Required Python version
- **Dependencies**: All production dependencies listed
- **Dev dependencies**: Development tools like pre-commit

## Important: Always Use Poetry Environment

**All project scripts must be run within the Poetry environment** to ensure:
- All dependencies are available
- Correct Python version is used
- Isolated, reproducible environment
- No conflicts with system packages

---

# Pre-commit Configuration

## Overview
This project uses pre-commit hooks to ensure code quality and consistency. The `.pre-commit-config.yaml` file configures automated checks that run every time before a commit is made, helping to catch issues early and maintain high code standards.

## Setup with Poetry

### 1. Install pre-commit hooks
```bash
# Activate Poetry environment and install hooks
poetry run pre-commit install
```

### 2. Run against all files
```bash
# Run all hooks on all files
poetry run pre-commit run --all-files
```

## Manual Execution

Run hooks manually using Poetry:

```bash
# Run all hooks on all files
poetry run pre-commit run --all-files

# Run a specific hook
poetry run pre-commit run black --all-files
poetry run pre-commit run mypy --all-files

# Run on specific files
poetry run pre-commit run --files figma.py slide_insertion.py
```

---

# Figma to SQL Generator Workflow (Internal Tool)

## Overview
This internal tool automates the process of extracting design and content data from Figma and generating SQL files to populate your company's presentation database.
It ensures that all slide layouts, blocks, styles, and related assets are consistently and safely transferred from design to production.

**⚠️ Important: All commands must be run within the Poetry environment using `poetry run` or `poetry shell`.**

---

## Data Flow & Table Structure

### Main Tables Populated

- **SlideLayout**: Stores metadata for each slide layout (name, type, number, etc.).
- **BlockLayout**: Stores each block (text, image, figure, etc.) belonging to a slide.
- **BlockLayoutStyles**: Stores style information for each block (color, font, alignment, etc.).
- **BlockLayoutDimensions**: Stores position and size for each block.
- **BlockLayoutLimit**: stores the amount of words for a block
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

**All Commands (Cross-Platform):**
```bash
# 1. Extract from Figma
poetry run python figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 -1 --output-dir my_output

# 2. Insert into PresentationPalette
# manual mode
poetry run python insert_presentation_palette.py --json my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# auto mode
poetry run python insert_presentation_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 3. Insert into BlockLayoutConfig
# manual mode
poetry run python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode manual
# auto mode
poetry run python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini

# 4. Match BlockLayoutConfig with PresentationPalette
poetry run python match_block_layout_presentation_palette.py

# 5. Generate SQL
poetry run python slide_insertion.py my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Validate SQL
poetry run python sql_validator.py --input-dir my_sql_output

# 7. Apply SQL to DB
poetry run python sql_pollution.py

# 8. Delete from the DB (blocks, slides, images)
poetry run python slide_deletion.py

# 9. Update blocks (cleanup old and insert new)
poetry run python update_blocks.py my_sql_output_old my_sql_output --output-dir final

# 10. Create user accounts (optional)
poetry run python account_creation.py

# 11. Generate image options from S3 bucket
poetry run python generate_image_options_sql.py
```

**Alternative: Using Poetry Shell**
```bash
# Activate Poetry shell once
poetry shell

# Then run all commands without poetry run prefix
python figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 -1 --output-dir my_output
python insert_presentation_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv
python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini
python match_block_layout_presentation_palette.py
python slide_insertion.py my_output/sql_generator_input.json --output-dir my_sql_output
python sql_validator.py --input-dir my_sql_output
python sql_pollution.py
python slide_deletion.py
python update_blocks.py my_sql_output_old my_sql_output --output-dir final
python account_creation.py
python generate_image_options_sql.py

# Exit shell when done
exit
```

---

## Configuration File: `config.py`
- **Centralizes all settings** for the workflow.
- Stores Figma API credentials, default values, slide/block mappings, color and watermark settings, and logic for categorizing slides/blocks.
- **Ensures consistency** between extraction and SQL generation.

---

## Script Descriptions

### `figma.py`
- **Purpose:** Extracts and normalizes design data from Figma files for SQL generation
- **Functionality:**
  - Connects to Figma API using authentication tokens
  - Extracts slides, blocks, styles, and metadata from Figma designs
  - Normalizes block types, colors, fonts, and dimensions
  - Handles z-index ordering and corner radius extraction
  - Processes comments and text content from Figma nodes
  - Validates font weights against allowed values (300, 400, 700)
  - Generates two output files: raw extraction and SQL-ready data
- **Configuration:**
  - Requires `config.py` with Figma API credentials and mappings
  - Uses environment variables for FIGMA_FILE_ID and FIGMA_TOKEN
  - Supports filtering by slide numbers, block types, or containers
- **Dependencies:** `requests`, `json`, `os`, `re`, `logging`, `config`
- **Usage:** `poetry run python figma.py --mode slides --slides 1 2 3 --output-dir my_output`

### `slide_insertion.py`
- **Purpose:** Generates SQL files from normalized Figma data for database population
- **Functionality:**
  - Reads normalized JSON from figma.py output
  - Generates INSERT statements for all database tables
  - Handles slide layouts, blocks, styles, dimensions, and figures
  - Supports auto and manual modes for data processing
  - Creates SQL files organized by slide layout type
  - Validates data against config.py constraints
  - Generates comprehensive SQL instructions and documentation
- **Configuration:**
  - Uses `config.py` for all default values and mappings
  - Requires `database.ini` for database connection parameters
  - Supports custom output directories and file naming
- **Dependencies:** `json`, `os`, `logging`, `config`, `argparse`, `uuid_utils`
- **Usage:** `poetry run python slide_insertion.py input.json --output-dir sql_output`

### `sql_validator.py`
- **Purpose:** Validates generated SQL files for syntax and referential integrity
- **Functionality:**
  - Checks SQL syntax for all generated files
  - Validates foreign key relationships between tables
  - Ensures required fields are present and properly formatted
  - Verifies UUID formats and data type consistency
  - Generates detailed validation reports with error locations
  - Supports batch validation of entire SQL directories
- **Configuration:**
  - Reads `database.ini` for connection parameters
  - Uses config.py for validation rules and constraints
  - Supports custom validation rules and error reporting
- **Dependencies:** `psycopg2`, `os`, `logging`, `config`, `argparse`
- **Usage:** `poetry run python sql_validator.py --input-dir sql_output`

### `sql_pollution.py`
- **Purpose:** Executes validated SQL files against PostgreSQL database
- **Functionality:**
  - Connects to PostgreSQL database using connection parameters
  - Executes SQL files in correct order to maintain referential integrity
  - Handles transaction management and rollback on errors
  - Supports batch execution of multiple SQL files
  - Provides detailed execution logs and error reporting
  - Ensures data consistency across all database tables
- **Configuration:**
  - Requires `database.ini` with PostgreSQL connection details
  - Uses config.py for execution order and table dependencies
  - Supports custom execution parameters and error handling
- **Dependencies:** `psycopg2`, `os`, `logging`, `config`, `argparse`
- **Usage:** `poetry run python sql_pollution.py`

### `slide_deletion.py`
- **Purpose:** Handles deletion of slides, blocks, and images from database
- **Functionality:**
  - Deletes slides and associated blocks by slide number
  - Removes specific block types across multiple slides
  - Handles cascading deletes for related data (figures, images, styles)
  - Supports selective deletion based on slide layout types
  - Generates deletion SQL files for review before execution
  - Provides safe deletion with confirmation prompts
- **Configuration:**
  - Uses `database.ini` for database connection
  - Supports custom deletion patterns and filters
  - Generates organized deletion SQL files by layout type
- **Dependencies:** `psycopg2`, `os`, `logging`, `config`, `argparse`
- **Usage:** `poetry run python slide_deletion.py --slides 1 2 3 --output-dir deletion_sql`

### `insert_presentation_palette.py`
- **Purpose:** Manages presentation palette configuration and color settings
- **Functionality:**
  - Inserts color palette data into PresentationPalette table
  - Supports manual and automatic mode for data insertion
  - Handles CSV mapping files for palette configuration
  - Validates color values and palette relationships
  - Generates palette SQL files for database insertion
  - Manages color settings IDs and default configurations
- **Configuration:**
  - Requires CSV mapping file for palette data
  - Uses `database.ini` for automatic mode database connection
  - Supports custom palette configurations and color schemes
- **Dependencies:** `csv`, `json`, `psycopg2`, `argparse`, `config`
- **Usage:** `poetry run python insert_presentation_palette.py --json input.json --mode auto --csv mapping.csv`

### `insert_block_layout_config.py`
- **Purpose:** Manages block layout configuration and styling settings
- **Functionality:**
  - Inserts block layout configuration data into database
  - Handles block type mappings and default styles
  - Supports manual and automatic configuration modes
  - Validates block layout relationships and constraints
  - Generates configuration SQL files for database insertion
  - Manages block layout IDs and style inheritance
- **Configuration:**
  - Uses JSON input from figma.py extraction
  - Requires `database.ini` for automatic mode
  - Supports custom block layout configurations
- **Dependencies:** `json`, `psycopg2`, `argparse`, `config`
- **Usage:** `poetry run python insert_block_layout_config.py --json input.json --mode auto`

### `match_block_layout_presentation_palette.py`
- **Purpose:** Matches block layout configurations with presentation palettes
- **Functionality:**
  - Creates relationships between block layouts and color palettes
  - Handles palette-block matching based on configuration rules
  - Generates matching SQL files for database insertion
  - Validates palette-block relationships and constraints
  - Supports custom matching rules and configurations
  - Manages palette-block index configurations
- **Configuration:**
  - Uses existing block layout and palette data from database
  - Requires `database.ini` for database connection
  - Supports custom matching algorithms and rules
- **Dependencies:** `psycopg2`, `json`, `argparse`, `config`
- **Usage:** `poetry run python match_block_layout_presentation_palette.py`

### `account_creation.py`
- **Purpose:** Creates complete user accounts with authentication, subscriptions, payments, and AB testing groups
- **Functionality:**
  - Creates user accounts with role-based access control (ADMIN, USER, MIIN, etc.)
  - Supports multiple authentication providers (local, Google, Yandex, VKontakte, Telegram)
  - Generates secure password hashes using scrypt algorithm (compatible with Node.js)
  - Creates subscriptions with payment tracking and symbol purchases
  - Manages user balances and subscription symbols
  - Creates AB testing group assignments for user segmentation
  - Supports both automatic (direct DB) and manual (SQL generation) modes
  - Generates UUID7 time-ordered identifiers for better database performance
- **Configuration:**
  - Requires `database.ini` with PostgreSQL connection parameters
  - Uses Prisma schema for table structure validation
  - Supports custom subscription plans and payment statuses
- **Dependencies:** `psycopg2`, `uuid`, `hashlib`, `secrets`, `datetime`, `enum`
- **Usage:** `poetry run python account_creation.py` (interactive mode) or `poetry run python account_creation.py --mode auto`

### `migrate_images.py`
- **Purpose:** Migrates images from Google Drive to Yandex Cloud Object Storage
- **Functionality:**
  - Downloads images from a specified Google Drive folder
  - Uploads them to Yandex Cloud S3-compatible storage
  - Supports various image formats (JPG, PNG, GIF, BMP, WebP, TIFF, SVG)
  - Handles OAuth authentication with Google Drive API
  - Uses S3-compatible interface for Yandex Cloud storage
  - Preserves folder structure from Google Drive in Yandex Cloud
  - Recursively processes subfolders and their contents
  - Provides progress tracking and error handling
- **Configuration:**
  - Requires `.env` file with Yandex Cloud credentials and Google Drive folder ID
  - Requires `credentials.json` file from Google Cloud Console for Google Drive API access
  - Supports environment variables for configuration
- **Dependencies:** `boto3`, `google-api-python-client`, `google-auth-oauthlib`, `python-dotenv`, `uuid_utils`
- **Usage:** `poetry run python migrate_images.py`
- **How it works:**
  1. **Authentication:** Uses OAuth2 flow to authenticate with Google Drive API
  2. **Folder Discovery:** Recursively scans Google Drive folder for images and subfolders
  3. **Image Processing:** Downloads each image and uploads to Yandex Cloud with preserved path structure
  4. **Error Handling:** Continues processing even if individual files fail
  5. **Progress Tracking:** Shows download/upload progress and final statistics

### `update_blocks.py`
- **Purpose:** Generates cleanup statements for existing blocks and combines them with new insertion statements
- **Functionality:**
  - Processes old SQL files to find existing SlideLayout IDs in the database
  - Generates DELETE and UPDATE statements to safely remove old block data
  - Processes new SQL files and replaces new UUIDs with existing SlideLayout IDs
  - Maintains folder structure organization (title, 1cols, 2cols, etc.)
  - Creates cleanup files with `cleanup_` prefix and updated insertion files
  - Ensures foreign key constraint safety by updating UserBlockLayout.parentLayoutId first
  - Supports folder filtering for selective processing
  - Provides detailed statistics on processed slides and operations
- **Configuration:**
  - Requires `database.ini` with PostgreSQL connection parameters
  - Uses existing SlideLayout IDs from database to avoid creating duplicates
  - Maintains referential integrity by cleaning up in correct dependency order
- **Dependencies:** `psycopg2`, `os`, `re`, `argparse`, `shutil`, `datetime`, `pathlib`
- **Usage:** `poetry run python update_blocks.py my_sql_output_old my_sql_output --output-dir final`
- **How it works:**
  1. **Database Connection:** Connects to PostgreSQL database to query existing SlideLayout records
  2. **File Matching:** Finds corresponding new SQL files for each old SQL file
  3. **SlideLayout Lookup:** Queries database to find existing SlideLayout IDs by name and number
  4. **Cleanup Generation:** Creates DELETE statements for existing block data in correct dependency order
  5. **ID Replacement:** Replaces new UUIDs with existing SlideLayout IDs in new SQL files
  6. **File Generation:** Creates combined SQL files with cleanup statements followed by new INSERT statements
  7. **Statistics:** Provides detailed counts of processed slides, operations, and generated files

### `generate_image_options_sql.py`
- **Purpose:** Scans S3 bucket for images and generates SQL statements for ImageOption insertion
- **Functionality:**
  - Scans Yandex Cloud S3 bucket for images using specified prefix
  - Generates UUID7 identifiers for each image following codebase patterns
  - Creates SQL INSERT statements for ImageOption table following Prisma schema
  - Supports various image formats (JPG, PNG, GIF, BMP, WebP, TIFF, SVG)
  - Groups images by folder structure for organized SQL output
  - Sets author fields to NULL as requested (no author information available)
  - Generates batch SQL with transaction support
  - Provides detailed logging to file and minimal console output
  - Creates comprehensive log files in `logs/` directory
- **Configuration:**
  - Requires `.env` file with Yandex Cloud credentials (YANDEX_STATIC_KEY, YANDEX_STATIC_SECRET, YANDEX_BUCKET_NAME)
  - Supports configurable S3 prefix for targeted scanning
  - Configurable image source type (brand, uploaded, unsplash, etc.)
  - Customizable output SQL file name
  - Interactive `.env` file creation if credentials are missing
- **Dependencies:** `boto3`, `python-dotenv`, `uuid-utils`
- **Usage:** `poetry run python generate_image_options_sql.py`
- **How it works:**
  1. **Credential Check:** Validates Yandex Cloud credentials and offers interactive setup
  2. **S3 Connection:** Authenticates with Yandex Cloud using static access keys
  3. **Bucket Access:** Verifies bucket access and permissions
  4. **Image Scanning:** Uses S3 paginator to efficiently scan bucket contents with prefix
  5. **Image Detection:** Filters objects by image file extensions
  6. **URL Generation:** Builds full URLs for each image in the bucket
  7. **SQL Generation:** Creates INSERT statements with UUID7 IDs and proper field mapping
  8. **Batch Processing:** Groups images by folder and generates organized SQL output
  9. **File Output:** Saves generated SQL to specified file with transaction support
  10. **Logging:** Provides detailed logs to file and summary to console
- **Environment Variables:**
  - `YANDEX_STATIC_KEY`: Yandex Cloud access key ID
  - `YANDEX_STATIC_SECRET`: Yandex Cloud secret access key
  - `YANDEX_BUCKET_NAME`: S3 bucket name
  - `S3_PREFIX`: Prefix to scan in bucket (default: "layouts/raiffeisen/miniatures/")
  - `IMAGE_SOURCE`: Image source type (default: "brand")
  - `OUTPUT_FILE`: Output SQL file name (default: "image_options.sql")
- **Output:**
  - SQL file with INSERT statements for ImageOption table
  - Detailed logs in `logs/image_options_generation.log`
  - Console summary with processed image count and file locations

---

# Poetry Управление зависимостями

## Обзор
Этот проект использует Poetry для управления зависимостями, предоставляя более надежный и современный подход к обработке Python зависимостей по сравнению с традиционными файлами `requirements.txt`.

## Что такое Poetry?
Poetry - это инструмент для управления зависимостями и упаковки в Python. Он позволяет объявлять библиотеки, от которых зависит ваш проект, и будет управлять (устанавливать/обновлять) их для вас.

## Установка

### 1. Установите Poetry
```bash
# Установить Poetry глобально
curl -sSL https://install.python-poetry.org | python3 -

# Или используя pip
pip install poetry
```

### 2. Установите зависимости проекта
```bash
# Установить все зависимости
poetry install

# Установить только продакшн зависимости
poetry install --no-dev
```

### 3. Активируйте виртуальное окружение
```bash
# Активировать Poetry shell
poetry shell

# Или запускать команды напрямую с poetry run
poetry run python figma.py --help
```

## Использование

### Добавление новых зависимостей
```bash
# Добавить продакшн зависимость
poetry add requests

# Добавить зависимость для разработки
poetry add --group dev pytest

# Добавить с конкретной версией
poetry add pandas==2.3.1
```

### Обновление зависимостей
```bash
# Обновить все зависимости
poetry update

# Обновить конкретную зависимость
poetry update pandas
```

### Запуск скриптов
```bash
# Запустить скрипты в окружении Poetry
poetry run python figma.py --help

# Или активировать shell сначала
poetry shell
python figma.py --help
```

### Управление виртуальным окружением
```bash
# Показать информацию о виртуальном окружении
poetry env info

# Удалить виртуальное окружение
poetry env remove python

# Создать новое виртуальное окружение
poetry env use python3.13
```

## Конфигурация

Проект использует `pyproject.toml` для конфигурации с:
- **Режим пакета отключен**: Это проект на основе скриптов, а не Python пакет
- **Python 3.13+**: Требуемая версия Python
- **Зависимости**: Все продакшн зависимости перечислены
- **Dev зависимости**: Инструменты разработки как pre-commit

## Важно: Всегда используйте окружение Poetry

**Все скрипты проекта должны запускаться в окружении Poetry** для обеспечения:
- Доступности всех зависимостей
- Использования правильной версии Python
- Изолированного, воспроизводимого окружения
- Отсутствия конфликтов с системными пакетами

---

# Конфигурация Pre-commit

## Обзор
Этот проект использует pre-commit хуки для обеспечения качества и согласованности кода. Файл `.pre-commit-config.yaml` настраивает автоматические проверки, которые запускаются каждый раз перед коммитом, помогая выявлять проблемы на ранней стадии и поддерживать высокие стандарты кода.

## Настройка с Poetry

### 1. Установите pre-commit хуки
```bash
# Активируйте окружение Poetry и установите хуки
poetry run pre-commit install
```

### 2. Запустите для всех файлов
```bash
# Запустить все хуки для всех файлов
poetry run pre-commit run --all-files
```

## Ручное выполнение

Запускайте хуки вручную используя Poetry:

```bash
# Запустить все хуки для всех файлов
poetry run pre-commit run --all-files

# Запустить конкретный хук
poetry run pre-commit run black --all-files
poetry run pre-commit run mypy --all-files

# Запустить для конкретных файлов
poetry run pre-commit run --files figma.py slide_insertion.py
```

---

# Рабочий процесс Figma → SQL (Внутренний инструмент)

## Обзор
Этот внутренний инструмент автоматизирует процесс извлечения данных из Figma и генерации SQL-файлов для заполнения корпоративной базы презентаций.
Он обеспечивает согласованную и безопасную передачу макетов слайдов, блоков, стилей и связанных ресурсов из дизайна в продакшн.

**⚠️ Важно: Все команды должны выполняться в окружении Poetry используя `poetry run` или `poetry shell`.**

---

## Поток данных и структура таблиц

### Основные таблицы

- **SlideLayout**: метаданные макета слайда (имя, тип, номер и т.д.)
- **BlockLayout**: каждый блок (текст, изображение, фигура и т.д.), принадлежащий слайду
- **BlockLayoutStyles**: стили для каждого блока (цвет, шрифт, выравнивание и т.д.)
- **BlockLayoutDimensions**: позиция и размер каждого блока
- **BlockLayoutLimit**: лимиты по количеству слов для блока
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

**Все команды (кроссплатформенные):**
```bash
# 1. Извлечение из Figma
poetry run python figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 -1 --output-dir my_output

# 2. Вставка в PresentationPalette
# ручной режим
poetry run python insert_presentation_palette.py --json my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# авто режим
poetry run python insert_presentation_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 3. Вставка в BlockLayoutConfig
# ручной режим
poetry run python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode manual
# авто режим
poetry run python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini

# 4. Сопоставление BlockLayoutConfig с PresentationPalette
poetry run python match_block_layout_presentation_palette.py

# 5. Генерация SQL
poetry run python slide_insertion.py my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Валидация SQL
poetry run python sql_validator.py --input-dir my_sql_output

# 7. Загрузка SQL в БД
poetry run python sql_pollution.py

# 8. Удаление из БД (блоков, слайдов, изображений)
poetry run python slide_deletion.py

# 9. Обновление блоков (очистка старых и вставка новых)
poetry run python update_blocks.py my_sql_output_old my_sql_output --output-dir final

# 10. Создание пользовательских аккаунтов (опционально)
poetry run python account_creation.py

# 11. Генерация опций изображений из S3 bucket
poetry run python generate_image_options_sql.py
```

**Альтернатива: Использование Poetry Shell**
```bash
# Активировать Poetry shell один раз
poetry shell

# Затем запускать все команды без префикса poetry run
python figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 -1 --output-dir my_output
python insert_presentation_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv
python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini
python match_block_layout_presentation_palette.py
python slide_insertion.py my_output/sql_generator_input.json --output-dir my_sql_output
python sql_validator.py --input-dir my_sql_output
python sql_pollution.py
python slide_deletion.py
python update_blocks.py my_sql_output_old my_sql_output --output-dir final
python account_creation.py
python generate_image_options_sql.py

# Выйти из shell когда закончили
exit
```

---

## Конфигурационный файл: `config.py`
- **Централизует все настройки** для пайплайна
- Хранит Figma API, значения по умолчанию, маппинги слайдов/блоков, цвета, вотермарки и логику категоризации
- **Гарантирует согласованность** между извлечением и генерацией SQL

---

## Описание скриптов

### `figma.py`
- **Назначение:** Извлекает и нормализует данные дизайна из файлов Figma для генерации SQL
- **Использование:** `poetry run python figma.py --mode slides --slides 1 2 3 --output-dir my_output`

### `slide_insertion.py`
- **Назначение:** Генерирует SQL файлы из нормализованных данных Figma для заполнения базы данных
- **Использование:** `poetry run python slide_insertion.py input.json --output-dir sql_output`

### `sql_validator.py`
- **Назначение:** Проверяет сгенерированные SQL файлы на синтаксис и ссылочную целостность
- **Использование:** `poetry run python sql_validator.py --input-dir sql_output`

### `sql_pollution.py`
- **Назначение:** Выполняет проверенные SQL файлы в базе данных PostgreSQL
- **Использование:** `poetry run python sql_pollution.py`

### `slide_deletion.py`
- **Назначение:** Обрабатывает удаление слайдов, блоков и изображений из базы данных
- **Использование:** `poetry run python slide_deletion.py --slides 1 2 3 --output-dir deletion_sql`

### `account_creation.py`
- **Назначение:** Создает полные пользовательские аккаунты с аутентификацией, подписками, платежами и группами AB-тестирования
- **Использование:** `poetry run python account_creation.py` (интерактивный режим) или `poetry run python account_creation.py --mode auto`

### `migrate_images.py`
- **Назначение:** Переносит изображения из Google Drive в объектное хранилище Yandex Cloud
- **Использование:** `poetry run python migrate_images.py`

### `update_blocks.py`
- **Назначение:** Генерирует очистку для существующих блоков и объединяет их с новыми операторами вставки
- **Использование:** `poetry run python update_blocks.py my_sql_output_old my_sql_output --output-dir final`

### `generate_image_options_sql.py`
- **Назначение:** Сканирует S3 bucket для изображений и генерирует SQL-запросы для вставки в таблицу ImageOption
- **Функциональность:**
  - Сканирует Yandex Cloud S3 bucket для изображений с указанным префиксом
  - Генерирует UUID7 идентификаторы для каждого изображения, следуя паттернам кодовой базы
  - Создает SQL INSERT-запросы для таблицы ImageOption, следуя схеме Prisma
  - Поддерживает различные форматы изображений (JPG, PNG, GIF, BMP, WebP, TIFF, SVG)
  - Группирует изображения по структуре папок для организованного SQL-вывода
  - Устанавливает поля автора в NULL по запросу (информация об авторе недоступна)
  - Генерирует пакетные SQL-запросы с поддержкой транзакций
  - Предоставляет подробное логирование в файл и минимальный вывод в консоль
  - Создает комплексные файлы логов в директории `logs/`
- **Конфигурация:**
  - Требует файл `.env` с учетными данными Yandex Cloud (YANDEX_STATIC_KEY, YANDEX_STATIC_SECRET, YANDEX_BUCKET_NAME)
  - Поддерживает настраиваемый S3 префикс для целевого сканирования
  - Настраиваемый тип источника изображения (brand, uploaded, unsplash и т.д.)
  - Настраиваемое имя выходного SQL-файла
  - Интерактивное создание файла `.env`, если учетные данные отсутствуют
- **Зависимости:** `boto3`, `python-dotenv`, `uuid-utils`
- **Использование:** `poetry run python generate_image_options_sql.py`
- **Как работает:**
  1. **Проверка учетных данных:** Валидирует учетные данные Yandex Cloud и предлагает интерактивную настройку
  2. **S3 подключение:** Аутентифицируется с Yandex Cloud используя статические ключи доступа
  3. **Доступ к bucket:** Проверяет доступ к bucket и разрешения
  4. **Сканирование изображений:** Использует S3 пагинатор для эффективного сканирования содержимого bucket с префиксом
  5. **Обнаружение изображений:** Фильтрует объекты по расширениям файлов изображений
  6. **Генерация URL:** Строит полные URL для каждого изображения в bucket
  7. **Генерация SQL:** Создает INSERT-запросы с UUID7 ID и правильным маппингом полей
  8. **Пакетная обработка:** Группирует изображения по папкам и генерирует организованный SQL-вывод
  9. **Файловый вывод:** Сохраняет сгенерированный SQL в указанный файл с поддержкой транзакций
  10. **Логирование:** Предоставляет подробные логи в файл и сводку в консоль
- **Переменные окружения:**
  - `YANDEX_STATIC_KEY`: ID ключа доступа Yandex Cloud
  - `YANDEX_STATIC_SECRET`: Секретный ключ доступа Yandex Cloud
  - `YANDEX_BUCKET_NAME`: Имя S3 bucket
  - `S3_PREFIX`: Префикс для сканирования в bucket (по умолчанию: "layouts/raiffeisen/miniatures/")
  - `IMAGE_SOURCE`: Тип источника изображения (по умолчанию: "brand")
  - `OUTPUT_FILE`: Имя выходного SQL-файла (по умолчанию: "image_options.sql")
- **Вывод:**
  - SQL-файл с INSERT-запросами для таблицы ImageOption
  - Подробные логи в `logs/image_options_generation.log`
  - Сводка в консоли с количеством обработанных изображений и расположением файлов

---

**Все остальные скрипты также должны запускаться с `poetry run` для обеспечения правильной работы в изолированном окружении Poetry.**
