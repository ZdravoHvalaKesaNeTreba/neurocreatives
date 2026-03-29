import asyncio
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
import os
import logging
import time
from datetime import datetime
import json

from db.database import get_db_session, get_database, init_database, init_default_settings
from db.models import Post, Image, Analysis, Settings, ScheduleLog
from parser.telegram_parser import TelegramParser
from ai.image_analysis import ImageAnalyzer
from scheduler import scheduler
import config


app = FastAPI(
    title="Neurocreatives",
    description="Платформа для сбора и анализа рекламных креативов из Telegram",
    version="1.0.0"
)

# Обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Логируем детали ошибки валидации
    logger.error(f"❌ Validation Error for {request.method} {request.url.path}")
    logger.error(f"   Body: {exc.body}")
    logger.error(f"   Errors: {exc.errors()}")
    add_log("ERROR", f"❌ Validation Error: {exc.errors()}")
    
    # Возвращаем стандартный ответ
    return await request_validation_exception_handler(request, exc)

# Настройка статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="web/static"), name="static")
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")
templates = Jinja2Templates(directory="web/templates")


# Глобальные переменные для отслеживания статуса задач
parser_status = {"running": False, "message": "Готов к запуску"}
analysis_status = {"running": False, "message": "Готов к запуску"}

# Глобальный список для хранения последних логов
log_buffer = []
MAX_LOG_BUFFER_SIZE = 500

# Настройка логгера для перехвата логов
class LogCapture(logging.Handler):
    """Обработчик для перехвата логов в буфер."""
    
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                'level': record.levelname,
                'message': self.format(record)
            }
            log_buffer.append(log_entry)
            # Ограничиваем размер буфера
            if len(log_buffer) > MAX_LOG_BUFFER_SIZE:
                log_buffer.pop(0)
        except Exception:
            pass

# Настраиваем корневой логгер
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Добавляем наш обработчик
log_capture = LogCapture()
log_capture.setLevel(logging.INFO)
logger.addHandler(log_capture)

# Также добавляем для uvicorn логгера
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.addHandler(log_capture)
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addHandler(log_capture)


def add_log(level: str, message: str):
    """Добавить лог в буфер напрямую."""
    log_entry = {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'level': level,
        'message': message
    }
    log_buffer.append(log_entry)
    if len(log_buffer) > MAX_LOG_BUFFER_SIZE:
        log_buffer.pop(0)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения."""
    add_log("INFO", "🚀 Запуск Neurocreatives...")
    logger.info("🚀 Запуск Neurocreatives...")
    
    # Инициализация базы данных
    db = init_database(config.DATABASE_URL)
    db.create_tables()
    
    # Инициализация настроек по умолчанию
    init_default_settings()
    
    # Создаем папку для загрузок
    os.makedirs("downloads", exist_ok=True)
    
    # Запуск планировщика (можно отключить через DISABLE_SCHEDULER=true)
    if os.environ.get('DISABLE_SCHEDULER', '').lower() == 'true':
        add_log("INFO", "⏸️ Планировщик отключён (DISABLE_SCHEDULER=true)")
        logger.info("⏸️ Планировщик отключён (DISABLE_SCHEDULER=true)")
    else:
        try:
            scheduler.start_scheduler()
            add_log("INFO", "✓ Планировщик задач запущен")
            logger.info("✓ Планировщик задач запущен")
        except Exception as e:
            add_log("ERROR", f"⚠️ Ошибка запуска планировщика: {e}")
            logger.error(f"⚠️ Ошибка запуска планировщика: {e}")
    
    add_log("INFO", "✓ Приложение готово к работе")
    logger.info("✓ Приложение готово к работе")


@app.on_event("shutdown")
async def shutdown_event():
    """Корректная остановка при завершении приложения."""
    add_log("INFO", "🛑 Остановка приложения...")
    logger.info("🛑 Остановка приложения...")
    
    # Остановка планировщика
    try:
        scheduler.stop_scheduler()
        add_log("INFO", "✓ Планировщик остановлен")
        logger.info("✓ Планировщик остановлен")
    except Exception as e:
        logger.error(f"⚠️ Ошибка остановки планировщика: {e}")
    
    logger.info("✓ Приложение остановлено")


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
                "file_path": img.file_path if img.file_path and os.path.exists(img.file_path) else "/static/placeholder.png"
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
        else:
            # Если у поста вообще нет изображений - подставляем заглушку
            image_data = {
                "id": None,
                "file_path": "/static/placeholder.png"
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
    if post.images:
        for img in post.images:
            image_item = {
                "id": img.id,
                "file_path": img.file_path if img.file_path and os.path.exists(img.file_path) else "/static/placeholder.png",
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
    else:
        # Если у поста вообще нет изображений - подставляем заглушку
        images.append({
            "id": None,
            "file_path": "/static/placeholder.png",
            "analysis": None
        })
    
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
    from sqlalchemy import func
    
    total_posts = db.query(Post).count()
    total_images = db.query(Image).count()
    total_analyzed = db.query(Analysis).count()
    
    channels = db.query(Post.channel).distinct().all()
    channels_list = [ch[0] for ch in channels]
    
    # Вычисляем средние значения
    avg_stats = db.query(
        func.avg(Post.views).label('avg_views'),
        func.avg(Post.er).label('avg_er')
    ).first()
    
    avg_views = int(avg_stats.avg_views) if avg_stats.avg_views else 0
    avg_er = round(float(avg_stats.avg_er), 2) if avg_stats.avg_er else 0.0
    
    return {
        "total_posts": total_posts,
        "total_images": total_images,
        "total_analyzed": total_analyzed,
        "channels": channels_list,
        "avg_views": avg_views,
        "avg_er": avg_er,
        "parser_status": parser_status,
        "analysis_status": analysis_status
    }


async def run_parser_task(run_type: str = 'manual'):
    """
    Фоновая задача для запуска парсера.
    
    Args:
        run_type: Тип запуска ('manual' или 'auto')
    """
    global parser_status
    
    try:
        parser_status["running"] = True
        parser_status["message"] = "Парсинг запущен..."
        add_log("INFO", f"📡 Запуск парсера Telegram каналов ({run_type})...")
        logger.info(f"📡 Запуск парсера Telegram каналов ({run_type})...")
        
        # Получаем настройки глубины парсинга из БД
        db = get_database()
        with db.get_session() as session:
            parse_depth_setting = session.query(Settings).filter(Settings.key == 'parse_depth').first()
            parse_from_date_setting = session.query(Settings).filter(Settings.key == 'parse_from_date').first()
            
            parse_depth = parse_depth_setting.value if parse_depth_setting else 'today'
            parse_from_date = parse_from_date_setting.value if parse_from_date_setting else None
        
        # Читаем Telegram API ключи из БД (с фоллбэком на config)
        with db.get_session() as session:
            tg_api_id_setting = session.query(Settings).filter(Settings.key == 'telegram_api_id').first()
            tg_api_hash_setting = session.query(Settings).filter(Settings.key == 'telegram_api_hash').first()
            
            tg_api_id = int(tg_api_id_setting.value) if tg_api_id_setting and tg_api_id_setting.value else config.TELEGRAM_API_ID
            tg_api_hash = tg_api_hash_setting.value if tg_api_hash_setting and tg_api_hash_setting.value else config.TELEGRAM_API_HASH
        
        parser = TelegramParser(
            api_id=tg_api_id,
            api_hash=tg_api_hash
        )
        
        count = await parser.parse_channels(
            channels=config.CHANNELS_TO_PARSE,
            limit=100,
            parse_depth=parse_depth,
            parse_from_date=parse_from_date
        )
        
        # Логируем результат в БД
        with db.get_session() as session:
            log_entry = ScheduleLog(
                timestamp=datetime.utcnow(),
                run_type=run_type,
                status='success',
                images_parsed=count,
                images_analyzed=0
            )
            session.add(log_entry)
            session.commit()
        
        parser_status["running"] = False
        parser_status["message"] = f"Парсинг завершен. Собрано постов: {count}"
        add_log("INFO", f"✅ Парсинг завершен ({run_type}). Собрано постов: {count}")
        logger.info(f"✅ Парсинг завершен ({run_type}). Собрано постов: {count}")
        
    except Exception as e:
        # Логируем ошибку в БД
        try:
            db = get_database()
            with db.get_session() as session:
                log_entry = ScheduleLog(
                    timestamp=datetime.utcnow(),
                    run_type=run_type,
                    status='error',
                    images_parsed=0,
                    images_analyzed=0,
                    error_message=str(e)
                )
                session.add(log_entry)
                session.commit()
        except:
            pass
        
        parser_status["running"] = False
        parser_status["message"] = f"Ошибка: {str(e)}"
        add_log("ERROR", f"❌ Ошибка парсинга ({run_type}): {str(e)}")
        logger.error(f"❌ Ошибка парсинга ({run_type}): {str(e)}")


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
        add_log("INFO", "🔍 Запуск AI анализа изображений...")
        logger.info("🔍 Запуск AI анализа изображений...")
        
        # Создаем анализатор без API ключа - он получит его из БД
        analyzer = ImageAnalyzer()
        count = analyzer.analyze_all_unanalyzed()
        
        analysis_status["running"] = False
        analysis_status["message"] = f"Анализ завершен. Проанализировано: {count}"
        add_log("INFO", f"✅ Анализ завершен. Проанализировано: {count}")
        logger.info(f"✅ Анализ завершен. Проанализировано: {count}")
        
    except Exception as e:
        analysis_status["running"] = False
        analysis_status["message"] = f"Ошибка: {str(e)}"
        add_log("ERROR", f"❌ Ошибка анализа: {str(e)}")
        logger.error(f"❌ Ошибка анализа: {str(e)}", exc_info=True)


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


@app.get("/api/channels")
async def get_channels():
    """Получение текущего списка каналов для парсинга."""
    return {
        "channels": config.CHANNELS_TO_PARSE,
        "count": len(config.CHANNELS_TO_PARSE)
    }


@app.post("/api/channels")
async def update_channels(channels: List[str] = Body(...)):
    """
    Обновление списка каналов для парсинга.
    
    Args:
        channels: Список алиасов каналов (без @)
    """
    try:
        # Обновляем глобальную переменную
        config.CHANNELS_TO_PARSE = [ch.strip() for ch in channels if ch.strip()]
        
        # Обновляем .env файл
        env_path = ".env"
        channels_str = ",".join(config.CHANNELS_TO_PARSE)
        
        if os.path.exists(env_path):
            # Читаем существующий .env
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Обновляем строку CHANNELS_TO_PARSE
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('CHANNELS_TO_PARSE='):
                    lines[i] = f'CHANNELS_TO_PARSE={channels_str}\n'
                    updated = True
                    break
            
            # Если строки не было, добавляем
            if not updated:
                lines.append(f'\nCHANNELS_TO_PARSE={channels_str}\n')
            
            # Записываем обновленный .env
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        else:
            # Создаем новый .env файл
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f'CHANNELS_TO_PARSE={channels_str}\n')
        
        return {
            "status": "success",
            "message": f"Список каналов обновлен. Теперь {len(config.CHANNELS_TO_PARSE)} каналов.",
            "channels": config.CHANNELS_TO_PARSE
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении списка каналов: {str(e)}")


@app.get("/api/settings")
async def get_settings(db: Session = Depends(get_db_session)):
    """Получение всех настроек."""
    settings = db.query(Settings).all()
    
    result = {}
    for setting in settings:
        result[setting.key] = setting.value
    
    return result


@app.post("/api/settings")
async def update_settings(settings_data: dict, db: Session = Depends(get_db_session)):
    """
    Обновление настроек.
    
    Args:
        settings_data: Словарь с настройками {key: value}
    """
    try:
        for key, value in settings_data.items():
            # Ищем существующую настройку
            setting = db.query(Settings).filter(Settings.key == key).first()
            
            if setting:
                # Обновляем существующую
                setting.value = value
            else:
                # Создаем новую
                setting = Settings(key=key, value=value)
                db.add(setting)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Настройки успешно обновлены"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении настроек: {str(e)}")


@app.get("/api/logs")
async def get_logs():
    """Получение последних логов из буфера."""
    return {
        "logs": log_buffer[-100:],  # Возвращаем последние 100 логов
        "count": len(log_buffer)
    }


@app.get("/api/logs/stream")
async def stream_logs():
    """
    SSE (Server-Sent Events) для потоковой передачи логов в реальном времени.
    """
    async def generate():
        # Отправляем начальное сообщение
        yield f"data: {{'type': 'connected', 'message': 'Подключено к потоку логов'}}\n\n"
        
        # Отправляем последние 50 логов из буфера
        for log in log_buffer[-50:]:
            import json
            yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"
        
        # Запоминаем текущую позицию
        last_index = len(log_buffer)
        
        # Бесконечный цикл для отправки новых логов
        while True:
            # Проверяем наличие новых логов
            if len(log_buffer) > last_index:
                # Отправляем новые логи
                for log in log_buffer[last_index:]:
                    import json
                    yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"
                last_index = len(log_buffer)
            
            # Отправляем heartbeat каждые 15 секунд для поддержания соединения
            yield f": heartbeat\n\n"
            
            # Небольшая задержка перед следующей проверкой
            await asyncio.sleep(1)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Отключаем буферизацию для nginx
        }
    )


@app.get("/api/schedule")
async def get_schedule(db: Session = Depends(get_db_session)):
    """
    Получить текущие настройки расписания.
    """
    try:
        # Получаем настройки расписания из БД
        settings = db.query(Settings).filter(
            Settings.key.like('schedule_%')
        ).all()
        
        result = {}
        for setting in settings:
            key = setting.key.replace('schedule_', '')
            
            # Парсим значение в зависимости от ключа
            if key == 'enabled':
                result[key] = setting.value.lower() == 'true' if setting.value else False
            elif key == 'days':
                try:
                    result[key] = json.loads(setting.value) if setting.value else []
                except:
                    result[key] = []
            else:
                result[key] = setting.value
        
        # Значения по умолчанию
        defaults = {
            'enabled': False,
            'frequency': 'daily',
            'time': '08:00',
            'days': [],
            'end_type': 'indefinite',
            'end_date': None,
            'parse_depth': 'today',
            'parse_from_date': None
        }
        
        for key, default_value in defaults.items():
            if key not in result:
                result[key] = default_value
        
        # Получаем настройки глубины парсинга
        parse_depth_setting = db.query(Settings).filter(Settings.key == 'parse_depth').first()
        parse_from_date_setting = db.query(Settings).filter(Settings.key == 'parse_from_date').first()
        
        if parse_depth_setting:
            result['parse_depth'] = parse_depth_setting.value
        if parse_from_date_setting:
            result['parse_from_date'] = parse_from_date_setting.value
        
        # Добавляем статус планировщика
        status = scheduler.get_scheduler_status()
        result['scheduler_running'] = status['running']
        result['next_run'] = status['next_run']
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при получении настроек расписания: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.post("/api/schedule")
async def update_schedule(schedule_data: Dict[str, Any], db: Session = Depends(get_db_session)):
    """
    Обновить настройки расписания.
    
    Args:
        schedule_data: Настройки расписания
            - enabled: bool
            - frequency: str (daily/weekly/biweekly/monthly/custom)
            - time: str (HH:MM)
            - days: list (для custom)
            - end_type: str (indefinite/until_date)
            - end_date: str (ISO формат, опционально)
    """
    try:
        # Логируем полученные данные
        logger.info(f"📥 Получены данные расписания: {schedule_data}")
        add_log("INFO", f"📥 Получены данные расписания: {schedule_data}")
        
        # Валидация данных
        if 'enabled' not in schedule_data:
            raise HTTPException(status_code=400, detail="Отсутствует поле 'enabled'")
        
        if 'frequency' not in schedule_data:
            raise HTTPException(status_code=400, detail="Отсутствует поле 'frequency'")
        
        if 'time' not in schedule_data:
            raise HTTPException(status_code=400, detail="Отсутствует поле 'time'")
        
        # Проверка формата времени
        try:
            time_parts = schedule_data['time'].split(':')
            if len(time_parts) != 2:
                raise ValueError()
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except:
            raise HTTPException(status_code=400, detail="Неверный формат времени. Используйте HH:MM")
        
        # Сохраняем настройки в БД
        settings_to_save = {
            'schedule_enabled': str(schedule_data['enabled']),
            'schedule_frequency': schedule_data['frequency'],
            'schedule_time': schedule_data['time'],
            'schedule_days': json.dumps(schedule_data.get('days', [])),
            'schedule_end_type': schedule_data.get('end_type', 'indefinite'),
            'schedule_end_date': schedule_data.get('end_date', ''),
            'parse_depth': schedule_data.get('parse_depth', 'today'),
            'parse_from_date': schedule_data.get('parse_from_date', '')
        }
        
        for key, value in settings_to_save.items():
            setting = db.query(Settings).filter(Settings.key == key).first()
            
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = Settings(key=key, value=value)
                db.add(setting)
        
        db.commit()
        
        # Обновляем расписание в планировщике
        scheduler.update_schedule(schedule_data)
        
        add_log("INFO", f"📅 Расписание обновлено: {schedule_data['frequency']} в {schedule_data['time']}")
        logger.info(f"📅 Расписание обновлено: {schedule_data['frequency']} в {schedule_data['time']}")
        
        return {
            "status": "success",
            "message": "Расписание успешно обновлено"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обновлении расписания: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении расписания: {str(e)}")


@app.get("/api/schedule/logs")
async def get_schedule_logs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db_session)
):
    """
    Получить историю автозапусков.
    
    Args:
        limit: Количество записей (по умолчанию 50)
        offset: Смещение для пагинации (по умолчанию 0)
    """
    try:
        # Получаем общее количество записей
        total = db.query(ScheduleLog).count()
        
        # Получаем записи с учетом limit и offset
        logs = db.query(ScheduleLog).order_by(
            ScheduleLog.timestamp.desc()
        ).limit(limit).offset(offset).all()
        
        result = []
        for log in logs:
            result.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'run_type': log.run_type if hasattr(log, 'run_type') else 'auto',
                'status': log.status,
                'images_parsed': log.images_parsed,
                'images_analyzed': log.images_analyzed,
                'error_message': log.error_message
            })
        
        return {
            'logs': result,
            'count': total,  # Общее количество записей
            'limit': limit,
            'offset': offset
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении логов расписания: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.post("/api/telegram/reset-session")
async def reset_telegram_session():
    """Сброс сессии Telegram (удаление файла session)."""
    
    # Проверяем, не запущен ли парсер
    if parser_status.get("running"):
        raise HTTPException(
            status_code=409, 
            detail="Невозможно сбросить сессию: парсер сейчас работает. Дождитесь завершения."
        )
    
    try:
        session_files = ['parser_session.session', 'parser_session.session-journal']
        deleted = []
        errors = []
        
        for session_file in session_files:
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    deleted.append(session_file)
                    add_log("INFO", f"🗑️ Удалён файл сессии: {session_file}")
                    logger.info(f"🗑️ Удалён файл сессии: {session_file}")
                except OSError as e:
                    # Если файл заблокирован (Docker bind mount), перезаписываем пустым
                    try:
                        with open(session_file, 'wb') as f:
                            f.truncate(0)
                        deleted.append(f"{session_file} (очищен)")
                        add_log("INFO", f"🗑️ Файл сессии очищен: {session_file}")
                        logger.info(f"🗑️ Файл сессии очищен: {session_file}")
                    except OSError as e2:
                        errors.append(f"{session_file}: {str(e2)}")
                        add_log("WARNING", f"⚠️ Не удалось удалить/очистить {session_file}: {str(e2)}")
        
        if deleted and not errors:
            add_log("INFO", "✅ Сессия Telegram успешно сброшена")
            return {
                "status": "success",
                "message": f"Сессия Telegram сброшена. Удалено файлов: {len(deleted)}. При следующем запуске парсера потребуется повторная авторизация.",
                "deleted_files": deleted
            }
        elif deleted and errors:
            return {
                "status": "partial",
                "message": f"Частично сброшено. Удалено: {len(deleted)}, ошибок: {len(errors)}",
                "deleted_files": deleted,
                "errors": errors
            }
        elif errors:
            raise HTTPException(
                status_code=500, 
                detail=f"Не удалось удалить файлы сессии: {'; '.join(errors)}. Попробуйте перезапустить контейнер и повторить."
            )
        else:
            return {
                "status": "success",
                "message": "Файлы сессии не найдены (сессия уже сброшена или не была создана).",
                "deleted_files": []
            }
    except HTTPException:
        raise
    except Exception as e:
        add_log("ERROR", f"❌ Ошибка при сбросе сессии Telegram: {str(e)}")
        logger.error(f"❌ Ошибка при сбросе сессии Telegram: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при сбросе сессии: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
