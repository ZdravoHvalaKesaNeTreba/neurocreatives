# config.py

# --- Настройки для Telegram ---
# Получи свои api_id и api_hash на my.telegram.org
TELEGRAM_API_ID = 24628377
TELEGRAM_API_HASH = '2a52966d6223c3068e23d45e88c7a95a'

# Список Telegram каналов для парсинга
# Важно: твой аккаунт должен быть подписан на эти каналы
CHANNELS_TO_PARSE = [
    'GuerrillaMarketing',
    'Durov',
    'sostav'
]

# --- Настройки для OpenAI ---
# Получи API ключ на platform.openai.com
OPENAI_API_KEY = 'your-openai-api-key-here'

# --- Настройки базы данных ---
# PostgreSQL connection string (Yandex Cloud)
DATABASE_URL = 'postgresql://user1:db1user1db1@rc1b-rekalc1eaddo7kol.mdb.yandexcloud.net:6432/db_neurocreatives?sslmode=verify-full&target_session_attrs=read-write'

# --- Настройки сервера ---
HOST = '0.0.0.0'
PORT = 8000
