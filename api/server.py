import asyncio
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Request
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import os

from db.database import get_db_session, get_database, init_database
from db.models import Post, Image, Analysis
from parser.telegram_parser import TelegramParser
from ai.image_analysis import ImageAnalyzer
import config


app = FastAPI(
    title="Neurocreatives",
    description="Платформа для сбора и анализа рекламных креативов из Telegram",
    version="1.0.0"
)

# Настройка статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="web/static"), name="static")
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")
templates = Jinja2Templates(directory="web/templates")


# Глобальные переменные для отслеживания статуса задач
parser_status = {"running": False, "message": "Готов к запуску"}
analysis_status = {"running": False, "message": "Готов к запуску"}


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения."""
    print("🚀 Запуск Neurocreatives...")
    
    # Инициализация базы данных
    db = init_database(config.DATABASE_URL)
    db.create_tables()
    
    # Создаем папку для загрузок
    os.makedirs("downloads", exist_ok=True)
    
    print("✓ Приложение готово к работе")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/creatives")
async def get_creatives(
    limit: int = 50,
    offset: int = 0,
    channel: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """
    Получение списка креативов.
    
    Args:
        limit: Количество креативов
        offset: Смещение
        channel: Фильтр по каналу (опционально)
    """
    query = db.query(Post).options(
        joinedload(Post.images).joinedload(Image.analysis)
    ).order_by(Post.date.desc())
    
    if channel:
        query = query.filter(Post.channel == channel)
    
    total = query.count()
    posts = query.limit(limit).offset(offset).all()
    
    # Формируем ответ
    creatives = []
    for post in posts:
        image_data = None
        analysis_data = None
        
        if post.images:
            img = post.images[0]
            image_data = {
                "id": img.id,
                "file_path": img.file_path
            }
            
            if img.analysis:
                analysis_data = {
                    "scene": img.analysis.scene,
                    "objects": img.analysis.objects,
                    "emotion": img.analysis.emotion,
                    "creative_type": img.analysis.creative_type,
                    "text_present": img.analysis.text_present,
                    "visual_strength_score": img.analysis.visual_strength_score
                }
        
        creatives.append({
            "id": post.id,
            "channel": post.channel,
            "telegram_post_id": post.telegram_post_id,
            "text": post.text,
            "date": post.date.isoformat() if post.date else None,
            "views": post.views,
            "engagement": post.engagement,
            "er": round(post.er, 2),
            "post_url": post.post_url,
            "image": image_data,
            "analysis": analysis_data
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "creatives": creatives
    }


@app.get("/api/creative/{creative_id}")
async def get_creative(creative_id: int, db: Session = Depends(get_db_session)):
    """Получение детальной информации о креативе."""
    post = db.query(Post).options(
        joinedload(Post.images).joinedload(Image.analysis)
    ).filter(Post.id == creative_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Креатив не найден")
    
    # Формируем детальный ответ
    images = []
    for img in post.images:
        image_item = {
            "id": img.id,
            "file_path": img.file_path,
            "analysis": None
        }
        
        if img.analysis:
            image_item["analysis"] = {
                "scene": img.analysis.scene,
                "objects": img.analysis.objects,
                "emotion": img.analysis.emotion,
                "creative_type": img.analysis.creative_type,
                "text_present": img.analysis.text_present,
                "visual_strength_score": img.analysis.visual_strength_score
            }
        
        images.append(image_item)
    
    return {
        "id": post.id,
        "channel": post.channel,
        "telegram_post_id": post.telegram_post_id,
        "text": post.text,
        "date": post.date.isoformat() if post.date else None,
        "views": post.views,
        "forwards": post.forwards,
        "replies": post.replies,
        "reactions": post.reactions,
        "engagement": post.engagement,
        "er": round(post.er, 2),
        "post_url": post.post_url,
        "images": images
    }


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db_session)):
    """Получение общей статистики."""
    total_posts = db.query(Post).count()
    total_images = db.query(Image).count()
    total_analyzed = db.query(Analysis).count()
    
    channels = db.query(Post.channel).distinct().all()
    channels_list = [ch[0] for ch in channels]
    
    return {
        "total_posts": total_posts,
        "total_images": total_images,
        "total_analyzed": total_analyzed,
        "channels": channels_list,
        "parser_status": parser_status,
        "analysis_status": analysis_status
    }


async def run_parser_task():
    """Фоновая задача для запуска парсера."""
    global parser_status
    
    try:
        parser_status["running"] = True
        parser_status["message"] = "Парсинг запущен..."
        
        parser = TelegramParser(
            api_id=config.TELEGRAM_API_ID,
            api_hash=config.TELEGRAM_API_HASH
        )
        
        count = await parser.parse_channels(
            channels=config.CHANNELS_TO_PARSE,
            limit=100,
            today_only=True
        )
        
        parser_status["running"] = False
        parser_status["message"] = f"Парсинг завершен. Собрано постов: {count}"
        
    except Exception as e:
        parser_status["running"] = False
        parser_status["message"] = f"Ошибка: {str(e)}"


@app.post("/api/run-parser")
async def run_parser(background_tasks: BackgroundTasks):
    """Запуск парсера Telegram каналов."""
    if parser_status["running"]:
        return {"status": "already_running", "message": "Парсер уже запущен"}
    
    # Запускаем парсер в фоне
    background_tasks.add_task(run_parser_task)
    
    return {
        "status": "started",
        "message": "Парсер запущен в фоновом режиме"
    }


async def run_analysis_task():
    """Фоновая задача для запуска анализа."""
    global analysis_status
    
    try:
        analysis_status["running"] = True
        analysis_status["message"] = "Анализ запущен..."
        
        analyzer = ImageAnalyzer(api_key=config.OPENAI_API_KEY)
        count = analyzer.analyze_all_unanalyzed()
        
        analysis_status["running"] = False
        analysis_status["message"] = f"Анализ завершен. Проанализировано: {count}"
        
    except Exception as e:
        analysis_status["running"] = False
        analysis_status["message"] = f"Ошибка: {str(e)}"


@app.post("/api/run-analysis")
async def run_analysis(background_tasks: BackgroundTasks):
    """Запуск AI анализа изображений."""
    if analysis_status["running"]:
        return {"status": "already_running", "message": "Анализ уже запущен"}
    
    # Запускаем анализ в фоне
    background_tasks.add_task(run_analysis_task)
    
    return {
        "status": "started",
        "message": "Анализ запущен в фоновом режиме"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
