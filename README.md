# Project Structure

This repository is organized to support a full workflow from Figma design extraction to SQL generation and database population. Below is an overview of the main files and folders:

- `figma.py`: Extracts and normalizes data from Figma, outputs JSON files for further processing.
- `slide_insertion.py`: Reads normalized JSON and generates SQL files for each slide, handling all necessary tables.
- `sql_validator.py`: Validates generated SQL files for syntax and referential integrity before database insertion.
- `sql_pollution.py`: Executes validated SQL files against the target PostgreSQL database.
- `slide_deletion.py`: Handles deletion of slides, blocks, and images from the database, supporting selective and batch operations.
- `account_creation.py`: Creates user accounts with authentication, subscriptions, payments, and AB testing groups in the database.
- `insert_palette.py`, `insert_block_layout_config.py`, `match_block_layout_presentation_palette.py`: Scripts for managing palette and block layout configuration, including mapping and matching between Figma and database structures.
- `config.py`: Central configuration file for all scripts, storing Figma API credentials, mappings, and default values.
- `database.ini`: Stores database connection parameters for PostgreSQL.
- `schema.prisma`: Prisma schema file for Node.js backend integration.
- `requirements.txt`: Lists all Python dependencies including `uuid_utils` for UUID7 generation.
- `.pre-commit-config.yaml`: Pre-commit hooks configuration for automated code quality checks.
- `my_output/`, `my_sql_output/`: Output directories for extracted JSON and generated SQL files, respectively.
- `slide_deletion/`: Contains SQL files and scripts for deleting slides/blocks, organized by layout type (e.g., 1cols, 2cols, etc.).

---

# Pre-commit Configuration

## Overview
This project uses pre-commit hooks to ensure code quality and consistency. The `.pre-commit-config.yaml` file configures automated checks that run every time before a commit is made, helping to catch issues early and maintain high code standards.

## What is Pre-commit?
Pre-commit is a framework for managing and maintaining pre-commit hooks. It automatically runs various code quality tools before each commit, ensuring that all code meets the project's standards before it's submitted for review.

## Configuration File: `.pre-commit-config.yaml`

The pre-commit configuration includes the following hooks:

### Code Formatting & Style
- **Black**: Uncompromising Python code formatter that automatically formats code to PEP 8 standards
- **isort**: Automatically sorts and organizes Python imports alphabetically and by type
- **autoflake**: Removes unused imports and variables from Python code

### Code Quality & Linting
- **flake8**: Python linter that checks for style guide enforcement, programming errors, and complexity
- **mypy**: Static type checker for Python that ensures type safety and catches type-related errors

### Code Modernization
- **pyupgrade**: Automatically upgrades Python syntax to use newer language features

### Security & Best Practices
- **bandit**: Security linter that identifies common security issues in Python code
- **check-docstring-first**: Ensures docstrings are placed correctly in files
- **check-yaml**: Validates YAML file syntax
- **end-of-file-fixer**: Ensures files end with a newline
- **trailing-whitespace**: Removes trailing whitespace from files

## Installation & Setup

### 1. Install pre-commit
```bash
pip install pre-commit
```

### 2. Install the git hook scripts
```bash
pre-commit install
```

### 3. (Optional) Run against all files
```bash
pre-commit run --all-files
```

## How It Works

1. **Automatic Execution**: Pre-commit hooks run automatically every time you make a commit
2. **File Filtering**: Hooks only run on files that match their patterns (e.g., Python files for Black, mypy)
3. **Fail-Safe**: If any hook fails, the commit is blocked until issues are resolved
4. **Auto-Fix**: Many hooks automatically fix issues (like Black formatting) and stage the changes

## Manual Execution

You can run hooks manually on specific files or all files:

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run a specific hook
pre-commit run black --all-files
pre-commit run mypy --all-files

# Run on specific files
pre-commit run --files script/figma.py script/slide_insertion.py
```

## Configuration Details

### Line Length
- **Black & isort**: Configured for 350 characters to accommodate long lines in this project
- **flake8**: Set to ignore E203 (whitespace before ':') and allow 350 character lines

### Type Checking
- **mypy**: Configured with strict type checking to ensure robust type safety
- **No implicit Optional**: Enforces explicit Optional types for better code clarity

### Security Scanning
- **bandit**: Outputs results to `bandit-report.json` for detailed security analysis
- **Excludes**: Ignores test files and generated files

## Benefits

- **Consistent Code Style**: All code follows the same formatting standards
- **Early Error Detection**: Catches issues before they reach code review
- **Type Safety**: Ensures robust type annotations throughout the codebase
- **Security**: Identifies potential security vulnerabilities
- **Modern Code**: Automatically upgrades to newer Python syntax
- **Quality Assurance**: Maintains high code quality standards

---

# Конфигурация Pre-commit

## Обзор
Этот проект использует pre-commit хуки для обеспечения качества и согласованности кода. Файл `.pre-commit-config.yaml` настраивает автоматические проверки, которые запускаются каждый раз перед коммитом, помогая выявлять проблемы на ранней стадии и поддерживать высокие стандарты кода.

## Что такое Pre-commit?
Pre-commit - это фреймворк для управления и поддержки pre-commit хуков. Он автоматически запускает различные инструменты качества кода перед каждым коммитом, обеспечивая соответствие всего кода стандартам проекта перед отправкой на ревью.

## Файл конфигурации: `.pre-commit-config.yaml`

Конфигурация pre-commit включает следующие хуки:

### Форматирование и стиль кода
- **Black**: Бескомпромиссный форматтер Python кода, который автоматически форматирует код по стандартам PEP 8
- **isort**: Автоматически сортирует и организует импорты Python по алфавиту и типу
- **autoflake**: Удаляет неиспользуемые импорты и переменные из Python кода

### Качество и линтинг кода
- **flake8**: Python линтер, который проверяет соблюдение руководства по стилю, ошибки программирования и сложность
- **mypy**: Статический проверщик типов для Python, который обеспечивает безопасность типов и выявляет ошибки, связанные с типами

### Модернизация кода
- **pyupgrade**: Автоматически обновляет синтаксис Python для использования более новых языковых возможностей

### Безопасность и лучшие практики
- **bandit**: Линтер безопасности, который выявляет общие проблемы безопасности в Python коде
- **check-docstring-first**: Обеспечивает правильное размещение docstring в файлах
- **check-yaml**: Проверяет синтаксис YAML файлов
- **end-of-file-fixer**: Обеспечивает завершение файлов новой строкой
- **trailing-whitespace**: Удаляет завершающие пробелы из файлов

## Установка и настройка

### 1. Установите pre-commit
```bash
pip install pre-commit
```

### 2. Установите git hook скрипты
```bash
pre-commit install
```

### 3. (Опционально) Запустите для всех файлов
```bash
pre-commit run --all-files
```

## Как это работает

1. **Автоматическое выполнение**: Pre-commit хуки запускаются автоматически каждый раз при создании коммита
2. **Фильтрация файлов**: Хуки запускаются только для файлов, соответствующих их паттернам (например, Python файлы для Black, mypy)
3. **Безопасность**: Если любой хук не проходит, коммит блокируется до разрешения проблем
4. **Автоисправление**: Многие хуки автоматически исправляют проблемы (например, форматирование Black) и добавляют изменения в staging

## Ручное выполнение

Вы можете запускать хуки вручную для конкретных файлов или всех файлов:

```bash
# Запустить все хуки для всех файлов
pre-commit run --all-files

# Запустить конкретный хук
pre-commit run black --all-files
pre-commit run mypy --all-files

# Запустить для конкретных файлов
pre-commit run --files script/figma.py script/slide_insertion.py
```

## Детали конфигурации

### Длина строки
- **Black & isort**: Настроены на 350 символов для размещения длинных строк в этом проекте
- **flake8**: Настроен игнорировать E203 (пробелы перед ':') и разрешать строки в 350 символов

### Проверка типов
- **mypy**: Настроен со строгой проверкой типов для обеспечения надежной безопасности типов
- **No implicit Optional**: Принуждает явные Optional типы для лучшей ясности кода

### Сканирование безопасности
- **bandit**: Выводит результаты в `bandit-report.json` для детального анализа безопасности
- **Исключения**: Игнорирует тестовые файлы и сгенерированные файлы

## Преимущества

- **Согласованный стиль кода**: Весь код следует одинаковым стандартам форматирования
- **Раннее выявление ошибок**: Выявляет проблемы до того, как они попадут на ревью кода
- **Безопасность типов**: Обеспечивает надежные аннотации типов во всей кодовой базе
- **Безопасность**: Выявляет потенциальные уязвимости безопасности
- **Современный код**: Автоматически обновляет до более нового синтаксиса Python
- **Обеспечение качества**: Поддерживает высокие стандарты качества кода

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

**Windows:**
```bash
# 1. Extract from Figma
python figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output

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
python slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Validate SQL
python sql_validator.py --input-dir my_sql_output

# 7. Apply SQL to DB
python sql_pollution.py

# 8. Delete from the DB (blocks, slides, images)
python slide_deletion.py

# 9. Update blocks (cleanup old and insert new)
python update_blocks.py my_sql_output_old my_sql_output --output-dir final

# 10. Create user accounts (optional)
python account_creation.py
```

**macOS:**
```bash
# 1. Extract from Figma
python3 figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output

# 2. Insert into PresentationPalette
# manual mode
python3 insert_palette.py --json my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# auto mode
python3 insert_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 3. Insert into BlockLayoutConfig
# manual mode
python3 insert_block_layout_config.py --json my_output/sql_generator_input.json --mode manual
# auto mode
python3 insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini

# 4. Match BlockLayoutConfig with PresentationPalette
python3 match_block_layout_presentation_palette.py

# 5. Generate SQL
python3 slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Validate SQL
python3 sql_validator.py --input-dir my_sql_output

# 7. Apply SQL to DB
python3 sql_pollution.py

# 8. Delete from the DB (blocks, slides, images)
python3 slide_deletion.py

# 9. Update blocks (cleanup old and insert new)
python3 update_blocks.py my_sql_output_old my_sql_output --output-dir final

# 10. Create user accounts (optional)
python3 account_creation.py
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
- **Usage:** `python figma.py --mode slides --slides 1 2 3 --output-dir my_output`

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
- **Usage:** `python slide_insertion.py --auto-from-figma input.json --output-dir sql_output`

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
- **Usage:** `python sql_validator.py --input-dir sql_output`

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
- **Usage:** `python sql_pollution.py`

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
- **Usage:** `python slide_deletion.py --slides 1 2 3 --output-dir deletion_sql`

### `insert_palette.py`
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
- **Usage:** `python insert_palette.py --json input.json --mode auto --csv mapping.csv`

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
- **Usage:** `python insert_block_layout_config.py --json input.json --mode auto`

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
- **Usage:** `python match_block_layout_presentation_palette.py`

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
- **Usage:** `python account_creation.py` (interactive mode) or `python account_creation.py --mode auto`

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
- **Usage:** Run the script to migrate all images from Google Drive to Yandex Cloud storage
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
- **Usage:** `python update_blocks.py my_sql_output_old my_sql_output --output-dir final`
- **How it works:**
  1. **Database Connection:** Connects to PostgreSQL database to query existing SlideLayout records
  2. **File Matching:** Finds corresponding new SQL files for each old SQL file
  3. **SlideLayout Lookup:** Queries database to find existing SlideLayout IDs by name and number
  4. **Cleanup Generation:** Creates DELETE statements for existing block data in correct dependency order
  5. **ID Replacement:** Replaces new UUIDs with existing SlideLayout IDs in new SQL files
  6. **File Generation:** Creates combined SQL files with cleanup statements followed by new INSERT statements
  7. **Statistics:** Provides detailed counts of processed slides, operations, and generated files

---

# Структура проекта

Репозиторий организован для поддержки полного цикла: от извлечения данных из Figma до генерации SQL и наполнения базы данных. Вот краткое описание основных файлов и папок:

- `figma.py`: Извлекает и нормализует данные из Figma, формирует JSON для дальнейшей обработки.
- `slide_insertion.py`: Читает нормализованный JSON и генерирует SQL-файлы для каждого слайда, формируя все необходимые таблицы.
- `sql_validator.py`: Валидирует сгенерированные SQL-файлы на синтаксис и целостность связей перед загрузкой в базу.
- `sql_pollution.py`: Выполняет валидированные SQL-файлы в целевой базе PostgreSQL.
- `slide_deletion.py`: Удаляет слайды, блоки и изображения из базы, поддерживает выборочное и пакетное удаление.
- `account_creation.py`: Создает пользовательские аккаунты с аутентификацией, подписками, платежами и группами AB-тестирования в базе данных.
- `insert_palette.py`, `insert_block_layout_config.py`, `match_block_layout_presentation_palette.py`: Скрипты для управления палитрами и конфигурацией блоков, включая сопоставление между Figma и структурой базы.
- `config.py`: Центральный конфиг для всех скриптов, хранит параметры Figma API, маппинги и значения по умолчанию.
- `database.ini`: Параметры подключения к PostgreSQL.
- `schema.prisma`: Файл схемы Prisma для интеграции с Node.js backend.
- `requirements.txt`: Список всех Python зависимостей, включая `uuid_utils` для генерации UUID7.
- `.pre-commit-config.yaml`: Конфигурация pre-commit хуков для автоматических проверок качества кода.
- `my_output/`, `my_sql_output/`: Папки для вывода извлечённых JSON и сгенерированных SQL-файлов соответственно.
- `slide_deletion/`: Содержит SQL-файлы и скрипты для удаления слайдов/блоков, организованные по типу макета (например, 1cols, 2cols и т.д.).

---

# Конфигурация Pre-commit

## Обзор
Этот проект использует pre-commit хуки для обеспечения качества и согласованности кода. Файл `.pre-commit-config.yaml` настраивает автоматические проверки, которые запускаются каждый раз перед коммитом, помогая выявлять проблемы на ранней стадии и поддерживать высокие стандарты кода.

## Что такое Pre-commit?
Pre-commit - это фреймворк для управления и поддержки pre-commit хуков. Он автоматически запускает различные инструменты качества кода перед каждым коммитом, обеспечивая соответствие всего кода стандартам проекта перед отправкой на ревью.

## Файл конфигурации: `.pre-commit-config.yaml`

Конфигурация pre-commit включает следующие хуки:

### Форматирование и стиль кода
- **Black**: Бескомпромиссный форматтер Python кода, который автоматически форматирует код по стандартам PEP 8
- **isort**: Автоматически сортирует и организует импорты Python по алфавиту и типу
- **autoflake**: Удаляет неиспользуемые импорты и переменные из Python кода

### Качество и линтинг кода
- **flake8**: Python линтер, который проверяет соблюдение руководства по стилю, ошибки программирования и сложность
- **mypy**: Статический проверщик типов для Python, который обеспечивает безопасность типов и выявляет ошибки, связанные с типами

### Модернизация кода
- **pyupgrade**: Автоматически обновляет синтаксис Python для использования более новых языковых возможностей

### Безопасность и лучшие практики
- **bandit**: Линтер безопасности, который выявляет общие проблемы безопасности в Python коде
- **check-docstring-first**: Обеспечивает правильное размещение docstring в файлах
- **check-yaml**: Проверяет синтаксис YAML файлов
- **end-of-file-fixer**: Обеспечивает завершение файлов новой строкой
- **trailing-whitespace**: Удаляет завершающие пробелы из файлов

## Установка и настройка

### 1. Установите pre-commit
```bash
pip install pre-commit
```

### 2. Установите git hook скрипты
```bash
pre-commit install
```

### 3. (Опционально) Запустите для всех файлов
```bash
pre-commit run --all-files
```

## Как это работает

1. **Автоматическое выполнение**: Pre-commit хуки запускаются автоматически каждый раз при создании коммита
2. **Фильтрация файлов**: Хуки запускаются только для файлов, соответствующих их паттернам (например, Python файлы для Black, mypy)
3. **Безопасность**: Если любой хук не проходит, коммит блокируется до разрешения проблем
4. **Автоисправление**: Многие хуки автоматически исправляют проблемы (например, форматирование Black) и добавляют изменения в staging

## Ручное выполнение

Вы можете запускать хуки вручную для конкретных файлов или всех файлов:

```bash
# Запустить все хуки для всех файлов
pre-commit run --all-files

# Запустить конкретный хук
pre-commit run black --all-files
pre-commit run mypy --all-files

# Запустить для конкретных файлов
pre-commit run --files script/figma.py script/slide_insertion.py
```

## Детали конфигурации

### Длина строки
- **Black & isort**: Настроены на 350 символов для размещения длинных строк в этом проекте
- **flake8**: Настроен игнорировать E203 (пробелы перед ':') и разрешать строки в 350 символов

### Проверка типов
- **mypy**: Настроен со строгой проверкой типов для обеспечения надежной безопасности типов
- **No implicit Optional**: Принуждает явные Optional типы для лучшей ясности кода

### Сканирование безопасности
- **bandit**: Выводит результаты в `bandit-report.json` для детального анализа безопасности
- **Исключения**: Игнорирует тестовые файлы и сгенерированные файлы

## Преимущества

- **Согласованный стиль кода**: Весь код следует одинаковым стандартам форматирования
- **Раннее выявление ошибок**: Выявляет проблемы до того, как они попадут на ревью кода
- **Безопасность типов**: Обеспечивает надежные аннотации типов во всей кодовой базе
- **Безопасность**: Выявляет потенциальные уязвимости безопасности
- **Современный код**: Автоматически обновляет до более нового синтаксиса Python
- **Обеспечение качества**: Поддерживает высокие стандарты качества кода

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

**Windows:**
```bash
# 1. Извлечение из Figma
python figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output

# 2. Вставка в PresentationPalette
# ручной режим
python insert_palette.py --json my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# авто режим
python insert_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 3. Вставка в BlockLayoutConfig
# ручной режим
python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode manual
# авто режим
python insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini

# 4. Сопоставление BlockLayoutConfig с PresentationPalette
python match_block_layout_presentation_palette.py

# 5. Генерация SQL
python slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Валидация SQL
python sql_validator.py --input-dir my_sql_output

# 7. Загрузка SQL в БД
python sql_pollution.py

# 8. Удаление из БД (блоков, слайдов, изображений)
python slide_deletion.py

# 6. Валидация SQL
python sql_validator.py --input-dir script/my_sql_output

# 7. Загрузка SQL в БД
python sql_pollution.py

# 8. Удаление из БД (блоков, слайдов, изображений)
python slide_deletion.py

# 9. Обновление блоков (очистка старых и вставка новых)
python update_blocks.py my_sql_output_old my_sql_output --output-dir final

# 10. Создание пользовательских аккаунтов (опционально)
python account_creation.py
```

**macOS:**
```bash
# 1. Извлечение из Figma
python3 figma.py --mode slides --slides 1 2 3 4 5 6 7 8 9 10 11 12 13 14 -1 --output-dir my_output

# 2. Вставка в PresentationPalette
# ручной режим
python3 insert_palette.py --json my_output/sql_generator_input.json --mode manual --csv presentation_palette_mapping.csv
# авто режим
python3 insert_palette.py --json my_output/sql_generator_input.json --mode auto --db database.ini --csv presentation_palette_mapping.csv

# 3. Вставка в BlockLayoutConfig
# ручной режим
python3 insert_block_layout_config.py --json my_output/sql_generator_input.json --mode manual
# авто режим
python3 insert_block_layout_config.py --json my_output/sql_generator_input.json --mode auto --db database.ini

# 4. Сопоставление BlockLayoutConfig с PresentationPalette
python3 match_block_layout_presentation_palette.py

# 5. Генерация SQL
python3 slide_insertion.py --auto-from-figma my_output/sql_generator_input.json --output-dir my_sql_output

# 6. Валидация SQL
python3 sql_validator.py --input-dir my_sql_output

# 7. Загрузка SQL в БД
python3 sql_pollution.py

# 8. Удаление из БД (блоков, слайдов, изображений)
python3 slide_deletion.py

# 9. Обновление блоков (очистка старых и вставка новых)
python3 update_blocks.py my_sql_output_old my_sql_output --output-dir final

# 10. Создание пользовательских аккаунтов (опционально)
python3 account_creation.py
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
- **Функциональность:**
  - Подключается к API Figma с использованием токенов аутентификации
  - Извлекает слайды, блоки, стили и метаданные из дизайнов Figma
  - Нормализует типы блоков, цвета, шрифты и размеры
  - Обрабатывает порядок z-index и извлечение радиуса углов
  - Обрабатывает комментарии и текстовое содержимое из узлов Figma
  - Проверяет толщину шрифтов на соответствие разрешенным значениям (300, 400, 700)
  - Генерирует два выходных файла: сырое извлечение и данные, готовые для SQL
- **Конфигурация:**
  - Требует `config.py` с учетными данными API Figma и сопоставлениями
  - Использует переменные окружения для FIGMA_FILE_ID и FIGMA_TOKEN
  - Поддерживает фильтрацию по номерам слайдов, типам блоков или контейнерам
- **Зависимости:** `requests`, `json`, `os`, `re`, `logging`, `config`
- **Использование:** `python figma.py --mode slides --slides 1 2 3 --output-dir my_output`

### `slide_insertion.py`
- **Назначение:** Генерирует SQL файлы из нормализованных данных Figma для заполнения базы данных
- **Функциональность:**
  - Читает нормализованный JSON из вывода figma.py
  - Генерирует операторы INSERT для всех таблиц базы данных
  - Обрабатывает макеты слайдов, блоки, стили, размеры и фигуры
  - Поддерживает автоматический и ручной режимы обработки данных
  - Создает SQL файлы, организованные по типам макетов слайдов
  - Проверяет данные на соответствие ограничениям config.py
  - Генерирует исчерпывающие SQL инструкции и документацию
- **Конфигурация:**
  - Использует `config.py` для всех значений по умолчанию и сопоставлений
  - Требует `database.ini` для параметров подключения к базе данных
  - Поддерживает пользовательские выходные каталоги и именование файлов
- **Зависимости:** `json`, `os`, `logging`, `config`, `argparse`, `uuid_utils`
- **Использование:** `python slide_insertion.py --auto-from-figma input.json --output-dir sql_output`

### `sql_validator.py`
- **Назначение:** Проверяет сгенерированные SQL файлы на синтаксис и ссылочную целостность
- **Функциональность:**
  - Проверяет синтаксис SQL для всех сгенерированных файлов
  - Проверяет отношения внешних ключей между таблицами
  - Обеспечивает присутствие и правильное форматирование обязательных полей
  - Проверяет форматы UUID и согласованность типов данных
  - Генерирует подробные отчеты о проверке с указанием местоположения ошибок
  - Поддерживает пакетную проверку целых каталогов SQL
- **Конфигурация:**
  - Читает `database.ini` для параметров подключения
  - Использует config.py для правил проверки и ограничений
  - Поддерживает пользовательские правила проверки и отчеты об ошибках
- **Зависимости:** `psycopg2`, `os`, `logging`, `config`, `argparse`
- **Использование:** `python sql_validator.py --input-dir sql_output`

### `sql_pollution.py`
- **Назначение:** Выполняет проверенные SQL файлы в базе данных PostgreSQL
- **Функциональность:**
  - Подключается к базе данных PostgreSQL, используя параметры подключения
  - Выполняет SQL файлы в правильном порядке для поддержания ссылочной целостности
  - Обрабатывает управление транзакциями и откат при ошибках
  - Поддерживает пакетное выполнение нескольких SQL файлов
  - Предоставляет подробные журналы выполнения и отчеты об ошибках
  - Обеспечивает согласованность данных во всех таблицах базы данных
- **Конфигурация:**
  - Требует `database.ini` с подробностями подключения PostgreSQL
  - Использует config.py для порядка выполнения и зависимостей таблиц
  - Поддерживает пользовательские параметры выполнения и обработку ошибок
- **Зависимости:** `psycopg2`, `os`, `logging`, `config`, `argparse`
- **Использование:** `python sql_pollution.py`

### `slide_deletion.py`
- **Назначение:** Обрабатывает удаление слайдов, блоков и изображений из базы данных
- **Функциональность:**
  - Удаляет слайды и связанные блоки по номеру слайда
  - Удаляет определенные типы блоков в нескольких слайдах
  - Обрабатывает каскадные удаления связанных данных (фигуры, изображения, стили)
  - Поддерживает селективное удаление на основе типов макетов слайдов
  - Генерирует SQL файлы удаления для просмотра перед выполнением
  - Обеспечивает безопасное удаление с запросами подтверждения
- **Конфигурация:**
  - Использует `database.ini` для подключения к базе данных
  - Поддерживает пользовательские шаблоны удаления и фильтры
  - Генерирует организованные SQL файлы удаления по типам макетов
- **Зависимости:** `psycopg2`, `os`, `logging`, `config`, `argparse`
- **Использование:** `python slide_deletion.py --slides 1 2 3 --output-dir deletion_sql`

### `insert_palette.py`
- **Назначение:** Управляет конфигурацией палитры презентации и настройками цветов
- **Функциональность:**
  - Вставляет данные цветовой палитры в таблицу PresentationPalette
  - Поддерживает ручной и автоматический режимы вставки данных
  - Обрабатывает CSV файлы сопоставления для конфигурации палитры
  - Проверяет значения цветов и отношения палитр
  - Генерирует SQL файлы палитры для вставки в базу данных
  - Управляет ID настроек цветов и конфигурациями по умолчанию
- **Конфигурация:**
  - Требует CSV файл сопоставления для данных палитры
  - Использует `database.ini` для подключения к базе данных в автоматическом режиме
  - Поддерживает пользовательские конфигурации палитр и цветовые схемы
- **Зависимости:** `csv`, `json`, `psycopg2`, `argparse`, `config`
- **Использование:** `python insert_palette.py --json input.json --mode auto --csv mapping.csv`

### `insert_block_layout_config.py`
- **Назначение:** Управляет конфигурацией макета блоков и настройками стилей
- **Функциональность:**
  - Вставляет данные конфигурации макета блоков в базу данных
  - Обрабатывает сопоставления типов блоков и стили по умолчанию
  - Поддерживает ручной и автоматический режимы конфигурации
  - Проверяет отношения макетов блоков и ограничения
  - Генерирует SQL файлы конфигурации для вставки в базу данных
  - Управляет ID макетов блоков и наследованием стилей
- **Конфигурация:**
  - Использует JSON ввод из извлечения figma.py
  - Требует `database.ini` для автоматического режима
  - Поддерживает пользовательские конфигурации макетов блоков
- **Зависимости:** `json`, `psycopg2`, `argparse`, `config`
- **Использование:** `python insert_block_layout_config.py --json input.json --mode auto`

### `match_block_layout_presentation_palette.py`
- **Назначение:** Сопоставляет конфигурации макетов блоков с палитрами презентации
- **Функциональность:**
  - Создает отношения между макетами блоков и цветовыми палитрами
  - Обрабатывает сопоставление палитра-блок на основе правил конфигурации
  - Генерирует SQL файлы сопоставления для вставки в базу данных
  - Проверяет отношения палитра-блок и ограничения
  - Поддерживает пользовательские правила сопоставления и конфигурации
  - Управляет конфигурациями индексов палитра-блок
- **Конфигурация:**
  - Использует существующие данные макетов блоков и палитр из базы данных
  - Требует `database.ini` для подключения к базе данных
  - Поддерживает пользовательские алгоритмы сопоставления и правила
- **Зависимости:** `psycopg2`, `json`, `argparse`, `config`
- **Использование:** `python match_block_layout_presentation_palette.py`

### `account_creation.py`
- **Назначение:** Создает полные пользовательские аккаунты с аутентификацией, подписками, платежами и группами AB-тестирования
- **Функциональность:**
  - Создает пользовательские аккаунты с ролевым доступом (ADMIN, USER, MIIN и т.д.)
  - Поддерживает несколько провайдеров аутентификации (local, Google, Yandex, VKontakte, Telegram)
  - Генерирует безопасные хеши паролей с использованием алгоритма scrypt (совместим с Node.js)
  - Создает подписки с отслеживанием платежей и покупками символов
  - Управляет балансами пользователей и символами подписок
  - Создает назначения групп AB-тестирования для сегментации пользователей
  - Поддерживает как автоматический (прямая БД), так и ручной (генерация SQL) режимы
  - Генерирует UUID7 временно-упорядоченные идентификаторы для лучшей производительности БД
- **Конфигурация:**
  - Требует `database.ini` с параметрами подключения PostgreSQL
  - Использует схему Prisma для валидации структуры таблиц
  - Поддерживает пользовательские планы подписок и статусы платежей
- **Зависимости:** `psycopg2`, `uuid`, `hashlib`, `secrets`, `datetime`, `enum`
- **Использование:** `python account_creation.py` (интерактивный режим) или `python account_creation.py --mode auto`

### `migrate_images.py`
- **Назначение:** Переносит изображения из Google Drive в объектное хранилище Yandex Cloud
- **Функциональность:**
  - Загружает изображения из указанной папки Google Drive
  - Выгружает их в S3-совместимое хранилище Yandex Cloud
  - Поддерживает различные форматы изображений (JPG, PNG, GIF, BMP, WebP, TIFF, SVG)
  - Обрабатывает OAuth аутентификацию с API Google Drive
  - Использует S3-совместимый интерфейс для хранилища Yandex Cloud
  - Сохраняет структуру папок из Google Drive в Yandex Cloud
  - Рекурсивно обрабатывает подпапки и их содержимое
  - Предоставляет отслеживание прогресса и обработку ошибок
- **Конфигурация:**
  - Требует файл `.env` с учетными данными Yandex Cloud и ID папки Google Drive
  - Требует файл `credentials.json` из Google Cloud Console для доступа к API Google Drive
  - Поддерживает переменные окружения для конфигурации
- **Зависимости:** `boto3`, `google-api-python-client`, `google-auth-oauthlib`, `python-dotenv`, `uuid_utils`
- **Использование:** Запустите скрипт для переноса всех изображений из Google Drive в хранилище Yandex Cloud
- **Как работает:**
  1. **Аутентификация:** Использует OAuth2 для аутентификации с API Google Drive
  2. **Обнаружение папок:** Рекурсивно сканирует папку Google Drive для поиска изображений и подпапок
  3. **Обработка изображений:** Загружает каждое изображение и выгружает в Yandex Cloud с сохранением структуры путей
  4. **Обработка ошибок:** Продолжает обработку даже при сбое отдельных файлов
  5. **Отслеживание прогресса:** Показывает прогресс загрузки/выгрузки и финальную статистику

### `update_blocks.py`
- **Назначение:** Генерирует очистку для существующих блоков и объединяет их с новыми операторами вставки
- **Функциональность:**
  - Обрабатывает старые SQL файлы, чтобы найти существующие ID макетов слайдов в базе данных
  - Генерирует операторы DELETE и UPDATE, чтобы безопасно удалить старые данные блока
  - Обрабатывает новые SQL файлы и заменяет новые UUID на существующие ID макетов слайдов
  - Сохраняет организацию структуры папок (название, 1cols, 2cols и т.д.)
  - Создает файлы очистки с префиксом `cleanup_` и обновленные файлы вставки
  - Обеспечивает безопасность ссылочных ограничений, обновляя UserBlockLayout.parentLayoutId сначала
  - Поддерживает фильтрацию папок для выборочной обработки
  - Предоставляет детальную статистику по обработанным слайдам и операциям
- **Конфигурация:**
  - Требует `database.ini` с параметрами подключения PostgreSQL
  - Использует существующие ID макетов слайдов из базы данных, чтобы избежать создания дубликатов
  - Сохраняет целостность ссылочных ограничений, очищая в правильном порядке зависимостей
- **Зависимости:** `psycopg2`, `os`, `re`, `argparse`, `shutil`, `datetime`, `pathlib`
- **Использование:** `python update_blocks.py my_sql_output_old my_sql_output --output-dir final`
- **Как работает:**
  1. **Подключение к БД:** Подключается к базе данных PostgreSQL для запроса существующих записей SlideLayout
  2. **Сопоставление файлов:** Находит соответствующие новые SQL файлы для каждого старого SQL файла
  3. **Поиск SlideLayout:** Запрашивает базу данных для поиска существующих ID макетов слайдов по имени и номеру
  4. **Генерация очистки:** Создает операторы DELETE для существующих данных блоков в правильном порядке зависимостей
  5. **Замена ID:** Заменяет новые UUID на существующие ID макетов слайдов в новых SQL файлах
  6. **Генерация файлов:** Создает объединенные SQL файлы с операторами очистки, за которыми следуют новые операторы INSERT
  7. **Статистика:** Предоставляет детальные подсчеты обработанных слайдов, операций и сгенерированных файлов
