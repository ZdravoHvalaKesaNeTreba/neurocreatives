import os
import asyncio
from datetime import date
from telethon.sync import TelegramClient
from sqlalchemy.orm import Session

from db.models import Post, Image
from db.database import get_database


class TelegramParser:
    """Парсер для сбора постов из Telegram каналов."""
    
    def __init__(self, api_id: int, api_hash: str, session_name: str = 'parser_session'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.downloads_folder = 'downloads'
    
    async def parse_channels(self, channels: list, limit: int = 100, today_only: bool = True):
        """
        Парсинг списка каналов.
        
        Args:
            channels: Список каналов для парсинга
            limit: Максимальное количество сообщений для проверки
            today_only: Парсить только сегодняшние посты
        
        Returns:
            Количество собранных постов
        """
        print("🔌 Подключение к Telegram...")
        
        async with TelegramClient(self.session_name, self.api_id, self.api_hash) as client:
            print("✓ Подключение успешно")
            
            # Создаем папку для загрузок
            os.makedirs(self.downloads_folder, exist_ok=True)
            
            today = date.today()
            total_posts = 0
            
            db = get_database()
            
            for channel_name in channels:
                print(f"\n📡 Парсинг канала: {channel_name}")
                
                try:
                    channel = await client.get_entity(channel_name)
                    channel_title = channel.title if hasattr(channel, 'title') else channel_name
                    channel_username = channel.username if hasattr(channel, 'username') else channel_name
                    
                    async for message in client.iter_messages(channel, limit=limit):
                        # Проверяем дату
                        if today_only and message.date.date() != today:
                            if message.date.date() < today:
                                print(f"  ⏸️  Достигнуты вчерашние посты")
                                break
                            continue
                        
                        # Проверяем наличие текста и фото
                        if message.text and message.photo:
                            print(f"  📥 Найден пост ID: {message.id}")
                            
                            # Скачиваем изображение
                            image_path = await message.download_media(file=self.downloads_folder)
                            
                            if image_path:
                                # Сохраняем в БД
                                with db.get_session() as session:
                                    self._save_post_to_db(
                                        session=session,
                                        channel_title=channel_title,
                                        channel_username=channel_username,
                                        message=message,
                                        image_path=image_path
                                    )
                                
                                total_posts += 1
                                print(f"  ✓ Пост сохранен в БД")
                
                except Exception as e:
                    print(f"  ❌ Ошибка при парсинге {channel_name}: {e}")
                    continue
            
            print(f"\n✓ Парсинг завершен. Собрано постов: {total_posts}")
            return total_posts
    
    def _save_post_to_db(self, session: Session, channel_title: str, channel_username: str, message, image_path: str):
        """Сохранение поста в базу данных."""
        
        # Формируем URL поста
        post_url = f"https://t.me/{channel_username}/{message.id}"
        
        # Получаем статистику поста
        views = message.views if hasattr(message, 'views') and message.views else 0
        forwards = message.forwards if hasattr(message, 'forwards') and message.forwards else 0
        replies = message.replies.replies if hasattr(message, 'replies') and message.replies else 0
        
        # Считаем реакции
        reactions = 0
        if hasattr(message, 'reactions') and message.reactions:
            for reaction in message.reactions.results:
                reactions += reaction.count
        
        # Считаем engagement
        engagement = forwards + replies + reactions
        
        # Считаем ER (engagement rate)
        er = (engagement / views * 100) if views > 0 else 0.0
        
        # Проверяем, существует ли уже этот пост
        existing_post = session.query(Post).filter_by(
            channel=channel_title,
            telegram_post_id=message.id
        ).first()
        
        if existing_post:
            # Обновляем существующий пост
            existing_post.views = views
            existing_post.forwards = forwards
            existing_post.replies = replies
            existing_post.reactions = reactions
            existing_post.engagement = engagement
            existing_post.er = er
            post = existing_post
        else:
            # Создаем новый пост
            post = Post(
                channel=channel_title,
                telegram_post_id=message.id,
                text=message.text,
                date=message.date,
                views=views,
                forwards=forwards,
                replies=replies,
                reactions=reactions,
                engagement=engagement,
                er=er,
                image_path=image_path,
                post_url=post_url
            )
            session.add(post)
            session.flush()  # Получаем ID поста
        
        # Добавляем изображение, если еще не добавлено
        if not existing_post:
            image = Image(
                post_id=post.id,
                file_path=image_path
            )
            session.add(image)
