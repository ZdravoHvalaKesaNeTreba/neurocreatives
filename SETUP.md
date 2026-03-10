# Быстрая настройка Neurocreatives

## 1. Подготовка

### PostgreSQL

Убедитесь, что PostgreSQL установлен и запущен:

```bash
# Проверка статуса
psql --version

# Запуск (если не запущен)
# macOS:
brew services start postgresql@14

# Linux:
sudo systemctl start postgresql
```

### Создание базы данных

```bash
# Подключитесь к PostgreSQL
psql postgres

# Создайте базу
CREATE DATABASE neurocreatives;

# Выход
\q
```

## 2. Настройка проекта

### Установка зависимостей

```bash
# Создайте виртуальное окружение
python3 -m venv venv

# Активируйте его
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Установите зависимости
pip install -r requirements.txt
```

### Конфигурация

Отредактируйте [`config.py`](config.py):

```python
# 1. Telegram API (получите на my.telegram.org)
TELEGRAM_API_ID = 24628377  # замените на свой
TELEGRAM_API_HASH = '2a52966d6223c3068e23d45e88c7a95a'  # замените на свой

# 2. Каналы для парсинга
CHANNELS_TO_PARSE = [
    'GuerrillaMarketing',
    'Durov',
    'sostav'
]

# 3. OpenAI API (получите на platform.openai.com)
OPENAI_API_KEY = 'sk-...'  # замените на свой ключ

# 4. База данных (по умолчанию должно работать)
DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/neurocreatives'
```

## 3. Запуск

```bash
python run.py
```

Откройте в браузере: **http://localhost:8000**

## 4. Первый запуск

### Telegram авторизация

При первом запуске парсера Telethon попросит:

1. Номер телефона (с +7 для России)
2. Код из Telegram
3. Пароль (если есть двухфакторная аутентификация)

Сессия сохранится в файл `parser_session.session` и больше не потребует авторизации.

### Порядок действий

1. Откройте http://localhost:8000
2. Нажмите **"Запустить парсер"** - соберет посты за сегодня
3. Подождите завершения (статус в сайдбаре)
4. Нажмите **"Запустить анализ"** - AI проанализирует изображения
5. Обновите страницу для просмотра результатов

## 5. Проверка работы

### База данных

```bash
# Подключитесь к БД
psql -U postgres -d neurocreatives

# Проверьте таблицы
\dt

# Проверьте данные
SELECT COUNT(*) FROM posts;
SELECT COUNT(*) FROM images;
SELECT COUNT(*) FROM analysis;

# Выход
\q
```

### Логи

Смотрите вывод в терминале, где запущен `python run.py`

## Готово! 🎉

Если что-то не работает, проверьте:
- ✅ PostgreSQL запущен
- ✅ База данных создана
- ✅ API ключи правильные
- ✅ Виртуальное окружение активировано
- ✅ Все зависимости установлены

Подробная документация в [`README.md`](README.md)
