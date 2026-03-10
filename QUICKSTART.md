# 🚀 Быстрый старт Neurocreatives

## Минимальная инструкция для запуска

### 1️⃣ Установка PostgreSQL

```bash
# macOS
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2️⃣ Создание базы данных

```bash
psql postgres
CREATE DATABASE neurocreatives;
\q
```

### 3️⃣ Установка Python зависимостей

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4️⃣ Настройка config.py

Отредактируйте `config.py`:

```python
TELEGRAM_API_ID = ваш_api_id           # my.telegram.org
TELEGRAM_API_HASH = 'ваш_api_hash'     # my.telegram.org
OPENAI_API_KEY = 'sk-...'              # platform.openai.com
```

### 5️⃣ Запуск

```bash
python run.py
```

Откройте: **http://localhost:8000**

### 6️⃣ Использование

1. Нажмите **"Запустить парсер"**
2. При первом запуске введите номер телефона и код из Telegram
3. Дождитесь завершения парсинга
4. Нажмите **"Запустить анализ"**
5. Просматривайте креативы в интерфейсе

---

**Готово!** Подробности в [`README.md`](README.md)
