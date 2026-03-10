# main.py

# --- Импорт необходимых библиотек ---

# Telethon - это мощная библиотека для работы с API Telegram.
# Она позволяет "притворяться" обычным пользователем и делать почти все, что можно в приложении.
from telethon.sync import TelegramClient
from telethon.tl.types import InputMessagesFilterPhotos  # Для фильтрации сообщений с фото

# Pandas - это стандарт индустрии для работы с табличными данными в Python.
# Мы будем использовать ее для создания нашей таблицы перед выгрузкой.
import pandas as pd

# gspread - для удобной работы с Google Таблицами.
import gspread
# gspread_dataframe - для легкой загрузки данных из pandas DataFrame в Google Таблицу.
from gspread_dataframe import set_with_dataframe

# datetime - для работы с датами и временем. Нам нужно будет получить сегодняшний день.
from datetime import datetime, date

# os - для работы с операционной системой, например, чтобы создавать папки.
import os

# Импортируем наши настройки из файла config.py
import config

# --- Основная логика скрипта ---

# Определяем константу - имя папки, куда будем сохранять картинки
# Это удобно, чтобы не писать 'downloads' вручную по всему коду.
DOWNLOADS_FOLDER = 'downloads'


async def parse_channels():
    """
    Эта функция подключается к Telegram и парсит сообщения из каналов.
    Она 'асинхронная' (async), потому что Telethon работает с сетью и
    чтобы не "замораживать" программу в ожидании ответа от сервера,
    он выполняет другие задачи. 'await' говорит "подожди здесь, пока не закончится эта операция".
    """
    print("Начинаю подключение к Telegram...")

    # Создаем клиент Telegram.
    # 'parser_session' - это имя файла сессии. При первом запуске Telethon попросит
    # тебя ввести номер телефона, код и пароль (если есть), а потом сохранит сессию,
    # чтобы не входить каждый раз заново.
    # Мы используем 'async with', чтобы клиент автоматически подключился и отключился,
    # когда работа будет завершена.
    async with TelegramClient('parser_session', config.API_ID, config.API_HASH) as client:
        print("Подключение успешно!")

        # Создаем папку для скачивания картинок, если ее еще нет.
        # exist_ok=True означает, что если папка уже существует, ошибки не будет.
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

        # Готовим пустой список, куда будем складывать все данные о постах
        all_posts_data = []

        # Получаем сегодняшнюю дату, чтобы сравнивать с датой постов
        today = date.today()

        # Начинаем перебирать каналы из нашего списка в config.py
        for channel_name in config.CHANNELS_TO_PARSE:
            print(f"--- Начинаю парсинг канала: {channel_name} ---")

            # Получаем объект канала (entity) по его имени
            channel = await client.get_entity(channel_name)

            # Асинхронно перебираем сообщения в канале.
            # limit=100 означает, что мы посмотрим не больше 100 последних сообщений.
            # Этого обычно достаточно, чтобы найти все посты за день.
            async for message in client.iter_messages(channel, limit=100):
                # Проверяем, что дата поста - это сегодня.
                # message.date - это полный объект datetime, а .date() извлекает только дату.
                if message.date.date() == today:
                    # Проверяем, есть ли у сообщения и текст, и фото
                    if message.text and message.photo:
                        print(f"Найден пост за сегодня (ID: {message.id}). Скачиваю фото...")

                        # Скачиваем медиафайл (фото)
                        # path=DOWNLOADS_FOLDER указывает, куда сохранить файл.
                        # Функция возвращает путь к скачанному файлу.
                        image_path = await message.download_media(file=DOWNLOADS_FOLDER)

                        # Собираем всю информацию о посте в один словарь (dict)
                        post_info = {
                            "Канал": channel.title,  # Имя канала, которое видят пользователи
                            "Дата и время": message.date.strftime('%Y-%m-%d %H:%M:%S'),
                            # Форматируем дату в удобный вид
                            "Текст поста": message.text,
                            "Путь к картинке": image_path,  # Локальный путь к файлу
                            "Ссылка на пост": f"https://t.me/{channel.username}/{message.id}"
                        }

                        # Добавляем словарь с данными о посте в наш общий список
                        all_posts_data.append(post_info)
                elif message.date.date() < today:
                    # Если мы дошли до вчерашних постов, то дальше искать нет смысла.
                    # Это оптимизация, чтобы не проверять все 100 сообщений, если постов за сегодня было мало.
                    print("Дошли до вчерашних постов, перехожу к следующему каналу.")
                    break

    print("Парсинг всех каналов завершен.")
    # Функция возвращает список со всеми найденными постами
    return all_posts_data


def upload_to_google_sheet(data_frame):
    """
    Эта функция берет наши данные в виде таблицы (DataFrame) и загружает их в Google Таблицу.
    """
    print("Начинаю загрузку данных в Google Sheets...")

    # Авторизуемся в Google API с помощью нашего файла credentials.json
    # Указываем "области" (scopes) - к каким API мы хотим получить доступ.
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    gc = gspread.service_account(filename=config.GOOGLE_CREDENTIALS_FILE, scopes=scopes)

    # Открываем нашу таблицу по имени, которое мы указали в конфиге
    try:
        spreadsheet = gc.open(config.GOOGLE_SHEET_NAME)
        print(f"Таблица '{config.GOOGLE_SHEET_NAME}' успешно найдена.")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"ОШИБКА: Таблица с именем '{config.GOOGLE_SHEET_NAME}' не найдена!")
        print("Проверьте, что вы правильно указали имя и дали доступ сервисному аккаунту.")
        return  # Выходим из функции, если таблица не найдена

    # Выбираем первый лист в таблице (обычно он называется "Лист1")
    worksheet = spreadsheet.sheet1

    # Очищаем лист перед записью новых данных
    worksheet.clear()

    # Используем магию gspread-dataframe, чтобы загрузить всю нашу таблицу одной командой
    # resize=True автоматически изменит размер листа под наши данные.
    set_with_dataframe(worksheet, data_frame, resize=True)

    print("Данные успешно загружены в Google Таблицу!")


# Точка входа в программу.
# Конструкция 'if __name__ == "__main__":' означает, что этот код выполнится,
# только если мы запускаем именно этот файл (а не импортируем его в другой).
async def main():
    """Главная управляющая функция."""
    # Шаг 1: Запускаем парсер и ждем, пока он вернет нам данные
    parsed_data = await parse_channels()

    # Шаг 2: Проверяем, а нашли ли мы что-нибудь?
    if not parsed_data:
        print("За сегодня не найдено ни одного поста с текстом и картинкой. Завершаю работу.")
        return  # Выходим из программы, если данных нет

    # Шаг 3: Преобразуем наш список словарей в таблицу pandas (DataFrame)
    # Это очень удобная структура для анализа и выгрузки данных.
    df = pd.DataFrame(parsed_data)

    # Выводим первые 5 строк таблицы в консоль, чтобы убедиться, что все хорошо
    print("\n--- Предпросмотр собранных данных: ---")
    print(df.head())
    print("-------------------------------------\n")

    # Шаг 4: Загружаем эту таблицу в Google Sheets
    upload_to_google_sheet(df)

    print("\nРабота успешно завершена! Проверьте вашу Google Таблицу.")


# Запускаем нашу главную асинхронную функцию
if __name__ == '__main__':
    import asyncio

    # В Windows может потребоваться следующая строка для корректной работы asyncio
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

