# config.py
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# --- Настройки для Telegram ---
# Получи свои api_id и api_hash на my.telegram.org
TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', '24628377'))
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH', '2a52966d6223c3068e23d45e88c7a95a')

# Список Telegram каналов для парсинга
# Важно: твой аккаунт должен быть подписан на эти каналы
CHANNELS_TO_PARSE = os.getenv('CHANNELS_TO_PARSE', 'GuerrillaMarketing,Durov,sostav').split(',')

# --- Настройки для OpenAI ---
# Получи API ключ на platform.openai.com
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-openai-api-key-here')

# --- Настройки базы данных ---
# PostgreSQL connection string (Yandex Cloud)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user1:XXXXXXXXXXX@rc1b-rekalc1eaddo7kol.mdb.yandexcloud.net:6432/db_neurocreatives?sslmode=verify-full&target_session_attrs=read-write')

# --- Настройки сервера ---
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))

# --- Удалённый сервер с картинками ---
# Если задан, локально отсутствующие картинки будут загружаться с этого URL
# Пример: https://your-server.example.com  (без trailing slash)
REMOTE_IMAGES_BASE_URL = os.getenv('REMOTE_IMAGES_BASE_URL', 'https://neurocreatives.maksimprojects.space')
