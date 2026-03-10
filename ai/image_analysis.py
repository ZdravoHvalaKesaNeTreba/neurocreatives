import os
import base64
import json
from openai import OpenAI
from typing import Dict, Optional

from db.models import Image, Analysis
from db.database import get_database


class ImageAnalyzer:
    """Анализатор изображений с помощью OpenAI Vision."""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
        
        self.system_prompt = """You are analyzing an advertising creative.

Return JSON with:
- type: тип креатива (баннер, сторис, пост и т.д.)
- scene: описание сцены (кратко)
- objects: список объектов на изображении
- emotion: доминирующая эмоция
- category: категория рекламы (продукт, услуга, бренд и т.д.)
- text_present: есть ли текст на изображении (да/нет)
- visual_strength_score: оценка визуальной силы от 1 до 10

Be concise. Answer in Russian."""
    
    def analyze_image(self, image_path: str) -> Optional[Dict]:
        """
        Анализ изображения с помощью OpenAI Vision.
        
        Args:
            image_path: Путь к изображению
        
        Returns:
            Словарь с результатами анализа или None при ошибке
        """
        try:
            # Проверяем существование файла
            if not os.path.exists(image_path):
                print(f"  ❌ Файл не найден: {image_path}")
                return None
            
            # Читаем изображение и конвертируем в base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Определяем тип изображения
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }.get(ext, 'image/jpeg')
            
            # Формируем запрос к OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            # Извлекаем ответ
            content = response.choices[0].message.content
            
            # Парсим JSON из ответа
            # Иногда модель возвращает JSON внутри markdown блока
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            result = json.loads(content)
            return result
            
        except json.JSONDecodeError as e:
            print(f"  ❌ Ошибка парсинга JSON: {e}")
            print(f"  Ответ: {content}")
            return None
        except Exception as e:
            print(f"  ❌ Ошибка анализа изображения: {e}")
            return None
    
    def analyze_all_unanalyzed(self):
        """Анализ всех изображений без анализа в БД."""
        db = get_database()
        
        with db.get_session() as session:
            # Находим все изображения без анализа
            images = session.query(Image).outerjoin(Analysis).filter(
                Analysis.id == None
            ).all()
            
            total = len(images)
            if total == 0:
                print("✓ Все изображения уже проанализированы")
                return 0
            
            print(f"🔍 Найдено {total} изображений для анализа")
            
            analyzed = 0
            for idx, image in enumerate(images, 1):
                print(f"\n[{idx}/{total}] Анализ изображения ID: {image.id}")
                print(f"  Файл: {image.file_path}")
                
                result = self.analyze_image(image.file_path)
                
                if result:
                    # Сохраняем результат в БД
                    analysis = Analysis(
                        image_id=image.id,
                        scene=result.get('scene', ''),
                        objects=result.get('objects', ''),
                        emotion=result.get('emotion', ''),
                        creative_type=result.get('type', ''),
                        text_present=result.get('text_present', ''),
                        visual_strength_score=result.get('visual_strength_score', 0)
                    )
                    session.add(analysis)
                    session.commit()
                    analyzed += 1
                    print(f"  ✓ Анализ сохранен")
                else:
                    print(f"  ⚠️  Не удалось проанализировать")
            
            print(f"\n✓ Анализ завершен: {analyzed}/{total} изображений")
            return analyzed
