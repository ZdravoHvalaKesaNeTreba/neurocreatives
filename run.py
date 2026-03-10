#!/usr/bin/env python3
"""
Neurocreatives - Запуск локального сервера
"""

import uvicorn
import config

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Запуск Neurocreatives")
    print("=" * 60)
    print(f"\n📍 Сервер запускается на http://{config.HOST}:{config.PORT}")
    print("\n💡 Для остановки нажмите Ctrl+C\n")
    print("=" * 60)
    
    uvicorn.run(
        "api.server:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info"
    )
