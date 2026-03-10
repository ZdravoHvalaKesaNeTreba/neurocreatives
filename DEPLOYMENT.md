# Деплой Neurocreatives на Yandex Cloud VPS

Полная инструкция по развертыванию приложения на VPS с автоматическими обновлениями через GitHub Actions.

## 📋 Требования

- **VPS**: Yandex Cloud Compute (Ubuntu 20.04/22.04)
- **Память**: минимум 2GB RAM
- **Диск**: минимум 10GB
- **Домен**: (опционально) для SSL сертификата

## 🚀 Шаг 1: Подготовка VPS

### 1.1 Подключение к VPS

```bash
ssh your_username@your_vps_ip
```

### 1.2 Запуск скрипта настройки

```bash
# Скачать скрипт
curl -O https://raw.githubusercontent.com/ZdravoHvalaKesaNeTreba/neurocreatives/main/deploy/setup-vps.sh

# Дать права на выполнение
chmod +x setup-vps.sh

# Запустить
./setup-vps.sh
```

Скрипт автоматически установит:
- Docker & Docker Compose
- Nginx
- Git
- Клонирует репозиторий в `/opt/neurocreatives`

### 1.3 Настройка переменных окружения

```bash
cd /opt/neurocreatives
nano .env
```

Заполните все переменные:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
OPENAI_API_KEY=your_openai_key
DATABASE_URL=postgresql+psycopg://user:password@host:port/database
HOST=0.0.0.0
PORT=8000
```

Сохраните (`Ctrl+O`, `Enter`, `Ctrl+X`)

## 🌐 Шаг 2: Настройка Nginx

### 2.1 Редактирование конфигурации

```bash
sudo nano /etc/nginx/sites-available/neurocreatives
```

Замените `your-domain.com` на ваш домен (или IP адрес VPS).

### 2.2 Активация конфигурации

```bash
# Создать симлинк
sudo ln -s /etc/nginx/sites-available/neurocreatives /etc/nginx/sites-enabled/

# Проверить конфигурацию
sudo nginx -t

# Перезапустить Nginx
sudo systemctl reload nginx
```

### 2.3 Настройка SSL (опционально, но рекомендуется)

```bash
# Установка Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Certbot автоматически настроит HTTPS и обновит конфигурацию Nginx.

## 🐳 Шаг 3: Запуск приложения

### 3.1 Сборка и запуск Docker контейнера

```bash
cd /opt/neurocreatives
docker-compose up -d
```

### 3.2 Проверка статуса

```bash
# Проверить запущенные контейнеры
docker-compose ps

# Посмотреть логи
docker-compose logs -f
```

### 3.3 Тестирование

Откройте в браузере:
- `http://your-domain.com` (или `http://your_vps_ip`)
- Должна открыться главная страница Neurocreatives

## 🔄 Шаг 4: Настройка CI/CD с GitHub Actions

### 4.1 Генерация SSH ключа

На VPS:

```bash
# Создать SSH ключ (если еще нет)
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions

# Добавить публичный ключ в authorized_keys
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys

# Вывести приватный ключ (скопировать его)
cat ~/.ssh/github_actions
```

### 4.2 Добавление Secrets в GitHub

Перейдите в ваш репозиторий на GitHub:  
`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

Добавьте три секрета:

1. **VPS_HOST**
   - Value: `your_vps_ip` (например, `51.250.123.45`)

2. **VPS_USERNAME**
   - Value: `your_username` (например, `ubuntu`)

3. **VPS_SSH_KEY**
   - Value: содержимое файла `~/.ssh/github_actions` (приватный ключ)

### 4.3 Проверка работы

После добавления секретов, при каждом push в ветку `main` будет автоматически:

1. GitHub Actions подключится к VPS
2. Выполнит `git pull`
3. Пересоберет Docker образ
4. Перезапустит контейнер

Следить за процессом можно в `Actions` на GitHub.

## 📊 Управление приложением

### Остановка

```bash
cd /opt/neurocreatives
docker-compose down
```

### Перезапуск

```bash
cd /opt/neurocreatives
docker-compose restart
```

### Просмотр логов

```bash
# Все логи
docker-compose logs -f

# Последние 100 строк
docker-compose logs --tail=100
```

### Обновление вручную

```bash
cd /opt/neurocreatives
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🔧 Полезные команды

### Очистка Docker

```bash
# Удалить неиспользуемые образы
docker system prune -f

# Удалить все (ВНИМАНИЕ: удалит ВСЁ)
docker system prune -a -f
```

### Бэкапdeployvps

```bash
# Бэкап директории загрузок
tar -czf downloads_backup_$(date +%Y%m%d).tar.gz /opt/neurocreatives/downloads/

# Бэкап .env
cp /opt/neurocreatives/.env /opt/neurocreatives/.env.backup
```

### Мониторинг

```bash
# Использование ресурсов
docker stats

# Использование диска
df -h

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 🐛 Troubleshooting

### Приложение не запускается

```bash
# Проверить логи
docker-compose logs

# Проверить переменные окружения
cat .env

# Проверить подключение к БД
docker-compose exec neurocreatives python -c "from db.database import init_database; init_database(); print('OK')"
```

### Nginx ошибка 502

```bash
# Проверить что контейнер запущен
docker-compose ps

# Проверить что порт 8000 доступен
curl http://localhost:8000
```

### GitHub Actions не работает

1. Проверьте Secrets в настройках репозитория
2. Убедитесь что SSH ключ добавлен в `authorized_keys`
3. Проверьте логи в Actions на GitHub

## 📝 Дополнительно

### Автоматический перезапуск после сбоя

Docker Compose уже настроен с `restart: unless-stopped`, что означает автоматический перезапуск контейнера при сбое.

### Ротация логов

Добавьте в `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Затем перезапустите Docker:

```bash
sudo systemctl restart docker
```

## 🔒 Безопасность

1. **Файрвол**: настройте UFW для ограничения доступа
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Обновления**: регулярно обновляйте систему
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

3. **Секреты**: никогда не коммитьте `.env` файл в Git (уже добавлен в `.gitignore`)

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs -f`
2. Проверьте статус: `docker-compose ps`
3. Проверьте GitHub Actions: вкладка Actions в репозитории
4. Проверьте Nginx: `sudo nginx -t` и `sudo systemctl status nginx`

---

**Автор**: Neurocreatives Team  
**Репозиторий**: https://github.com/ZdravoHvalaKesaNeTreba/neurocreatives  
**Лицензия**: MIT
