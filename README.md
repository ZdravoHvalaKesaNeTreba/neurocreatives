# Neurocreatives

**AI-платформа для сбора и анализа рекламных креативов из Telegram**

Neurocreatives собирает креативы из Telegram каналов, анализирует их с помощью OpenAI Vision и предоставляет удобный веб-интерфейс для просмотра.

---

## 🎯 Возможности

- 📡 **Парсинг Telegram каналов** - автоматический сбор постов с изображениями
- 🔍 **AI анализ изображений** - OpenAI Vision анализирует креативы
- 💾 **PostgreSQL база данных** - надежное хранение данных
- 🌐 **Веб-интерфейс** - удобный просмотр креативов в стиле Yandex Ads
- 📊 **Аналитика** - статистика по постам, engagement rate

---

## 📋 Требования

- Python 3.9+
- PostgreSQL 14+
- Telegram API credentials (получить на [my.telegram.org](https://my.telegram.org))
- OpenAI API key (получить на [platform.openai.com](https://platform.openai.com))

---

## 🚀 Установка

### 1. Клонируйте репозиторий

```bash
cd neurocreatives
```

### 2. Создайте виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

### 3. Установите зависимости

```bash
pip install -r requirements.txt
```

### 4. Установите PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Скачайте установщик с [postgresql.org](https://www.postgresql.org/download/windows/)

### 5. Создайте базу данных

```bash
# Подключитесь к PostgreSQL
psql postgres

# Создайте базу данных
CREATE DATABASE neurocreatives;

# Создайте пользователя (если нужно)
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE neurocreatives TO postgres;

# Выход
\q
```

### 6. Настройте конфигурацию

Отредактируйте файл [`config.py`](config.py):

```python
# Telegram API
TELEGRAM_API_ID = ваш_api_id
TELEGRAM_API_HASH = 'ваш_api_hash'

# Каналы для парсинга
CHANNELS_TO_PARSE = [
    'GuerrillaMarketing',
    'Durov',
    'sostav'
]

# OpenAI API
OPENAI_API_KEY = 'ваш-openai-api-key'

# PostgreSQL
DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/neurocreatives'
```

---

## 🎮 Запуск

Запустите сервер:

```bash
python run.py
```

Откройте в браузере:

```
http://localhost:8000
```

---

## 📖 Использование

### 1. Запуск парсера

В веб-интерфейсе нажмите кнопку **"Запустить парсер"**

Парсер соберет все посты с изображениями за сегодня из настроенных каналов.

### 2. Запуск анализа

После парсинга нажмите **"Запустить анализ"**

AI проанализирует все изображения и определит:
- Тип креатива
- Сцену
- Объекты
- Эмоцию
- Визуальную силу (1-10)

### 3. Просмотр креативов

- Креативы отображаются в виде сетки
- Кликните на креатив для просмотра деталей
- Фильтруйте по каналам в боковой панели

---

## 🏗️ Структура проекта

```
neurocreatives/
├── parser/
│   └── telegram_parser.py      # Парсер Telegram каналов
├── ai/
│   └── image_analysis.py       # AI анализ изображений
├── db/
│   ├── models.py               # SQLAlchemy модели
│   └── database.py             # Подключение к БД
├── api/
│   └── server.py               # FastAPI сервер
├── web/
│   ├── templates/
│   │   └── index.html          # Главная страница
│   └── static/
│       ├── style.css           # Стили (Yandex Ads style)
│       └── app.js              # Frontend логика
├── downloads/                  # Скачанные изображения
├── config.py                   # Конфигурация
├── requirements.txt            # Зависимости
├── run.py                      # Запуск сервера
└── README.md                   # Документация
```

---

## 🗄️ База данных

### Таблицы

**posts** - посты из Telegram
- id, channel, telegram_post_id, text, date
- views, forwards, replies, reactions
- engagement, er (engagement rate)
- image_path, post_url

**images** - изображения из постов
- id, post_id, file_path

**analysis** - результаты AI анализа
- id, image_id
- scene, objects, emotion
- creative_type, text_present
- visual_strength_score

---

## 🔌 API

### `GET /api/creatives`
Получение списка креативов

Параметры:
- `limit` - количество (по умолчанию 50)
- `offset` - смещение
- `channel` - фильтр по каналу

### `GET /api/creative/{id}`
Детальная информация о креативе

### `GET /api/stats`
Общая статистика

### `POST /api/run-parser`
Запуск парсера

### `POST /api/run-analysis`
Запуск AI анализа

---

## 🎨 Дизайн

Интерфейс выполнен в стиле Yandex Ads / Yandex Start:

- Минималистичный UI
- Белый фон
- Светло-серые поверхности
- Легкие тени
- Акцентный желтый #FFCC00
- Grid layout (Pinterest style)
- Шрифт Inter

---

## ⚡ Команды разработчика

### Пересоздать базу данных

```python
from db.database import init_database

db = init_database()
db.drop_tables()
db.create_tables()
```

### Ручной запуск парсера

```python
import asyncio
from parser.telegram_parser import TelegramParser
import config

parser = TelegramParser(
    api_id=config.TELEGRAM_API_ID,
    api_hash=config.TELEGRAM_API_HASH
)

asyncio.run(parser.parse_channels(
    channels=config.CHANNELS_TO_PARSE,
    limit=100
))
```

### Ручной запуск анализа

```python
from ai.image_analysis import ImageAnalyzer
import config

analyzer = ImageAnalyzer(api_key=config.OPENAI_API_KEY)
analyzer.analyze_all_unanalyzed()
```

---

## 🐛 Устранение проблем

### База данных не подключается

Проверьте, что PostgreSQL запущен:
```bash
# macOS
brew services list

# Linux
sudo systemctl status postgresql

# Или проверьте подключение
psql -U postgres -d neurocreatives
```

### Ошибка Telegram авторизации

При первом запуске парсера Telethon запросит:
1. Номер телефона
2. Код из Telegram
3. Пароль (если установлен)

Данные сохранятся в файл `parser_session.session`

### OpenAI API ошибки

Проверьте:
1. Валидность API ключа
2. Баланс на аккаунте OpenAI
3. Лимиты API

---

## 📝 Лицензия

MIT License

---

## 👨‍💻 Автор

Neurocreatives - AI-powered творческая аналитика

---

## 🔄 Обновления

### v1.0.0
- Парсинг Telegram каналов
- AI анализ изображений
- Веб-интерфейс
- PostgreSQL база данных
- FastAPI backend

---

## 💡 Планы

- [ ] Фильтры и сортировка в UI
- [ ] Экспорт данных (CSV, JSON)
- [ ] Сравнение креативов
- [ ] Тренды и аналитика
- [ ] Поиск по креативам
- [ ] Теги и категории
- [ ] Избранное
- [ ] API документация (Swagger)

---

**Готово к запуску! 🚀**
