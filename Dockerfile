# =============================================================
# Neurocreatives — Production Dockerfile
# База данных: PostgreSQL на Yandex Cloud (sslmode=verify-full)
# Docker Compose не используется — запуск через docker run
# =============================================================

# ---------- Stage 1: builder ----------
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.13-slim

LABEL maintainer="neurocreatives" \
      description="Neurocreatives — Telegram parser + AI image analysis"

# Минимальные runtime-зависимости для psycopg (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Скачиваем корневой сертификат Yandex Cloud для sslmode=verify-full
RUN mkdir -p /usr/local/share/ca-certificates/yandex && \
    curl -sSL https://storage.yandexcloud.net/cloud-certs/CA.pem \
         -o /usr/local/share/ca-certificates/yandex/YandexInternalRootCA.crt && \
    update-ca-certificates

# Копируем установленные Python-пакеты из builder-стейджа
COPY --from=builder /install /usr/local

# Создаём непривилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Создаём директорию для скачанных медиафайлов (может быть примонтирована как volume)
RUN mkdir -p /app/downloads && chown -R appuser:appuser /app

# Копируем исходный код приложения
COPY --chown=appuser:appuser . .

# Переключаемся на непривилегированного пользователя
USER appuser

# Переменные окружения по умолчанию (переопределяются через --env / --env-file)
# PGSSLROOTCERT — путь к CA-сертификату Yandex Cloud (используется psycopg/libpq)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    PGSSLROOTCERT=/usr/local/share/ca-certificates/yandex/YandexInternalRootCA.crt

EXPOSE 8000

# Healthcheck — проверяем доступность API
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# Запуск приложения
CMD ["python", "run.py"]
