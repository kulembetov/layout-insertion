# ---------- base ----------
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Нерутовый пользователь (приятнее для безопасности)
ARG APP_USER=app
ARG APP_UID=1000
ARG APP_GID=1000
# Пробрасываем значения в ENV, чтобы были доступны во всех стадиях
ENV APP_USER=${APP_USER} APP_UID=${APP_UID} APP_GID=${APP_GID}

RUN groupadd -g "$APP_GID" "$APP_USER" && useradd -m -u "$APP_UID" -g "$APP_GID" "$APP_USER"

WORKDIR /app

# ---------- builder ----------
FROM base AS builder

# Билд-зависимости для компиляции популярных пакетов (psycopg2, cryptography и т.п.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry (только для стадии сборки)
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Создаём отдельный venv вне /app, чтобы bind-mount не перекрывал его
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" VIRTUAL_ENV=/opt/venv

# Poetry будет ставить в текущий venv, а не создавать свой
RUN poetry config virtualenvs.create false

# Копируем только манифесты зависимостей для кэширования слоёв
COPY pyproject.toml poetry.lock* ./

# Устанавливаем зависимости (без установки самого проекта)
RUN python -m pip install --upgrade pip setuptools wheel && \
    poetry install --no-interaction --no-ansi --sync --no-root

# Если проект должен быть установлен как пакет (скрипты/entry points), раскомментируй:
# COPY . .
# RUN poetry install --only main --no-interaction --no-ansi --sync

# ---------- runtime ----------
FROM base AS runtime

# Рантайм-библиотеки (PostgreSQL client lib для psycopg2/psycop)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
  && rm -rf /var/lib/apt/lists/*

# Переносим готовый venv
COPY --from=builder /opt/venv /opt/venv
ENV PYTHONPATH=/app DJANGO_SETTINGS_MODULE=django_app.config.settings
ENV PATH="/opt/venv/bin:$PATH" VIRTUAL_ENV=/opt/venv

# Копируем исходники сразу с нужным владельцем (в деве перекроется volume’ом .:/app)
COPY --chown=${APP_UID}:${APP_GID} . /app

# Права
USER ${APP_USER}

# Команда задаётся в docker-compose (web/bot), тут оставим no-op
CMD ["python", "--version"]
