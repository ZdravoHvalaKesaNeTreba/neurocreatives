# JavaScript Updates для планировщика с глубиной парсинга

## Статус: 85% готово, требуется финализация JavaScript

## Что уже сделано:

### Backend ✅
- [x] Модель `ScheduleLog` с полем `run_type` ('auto'/'manual')
- [x] Парсер поддерживает `parse_depth` (today/3days/from_date) и `parse_from_date`
- [x] API `/api/schedule` GET возвращает `parse_depth` и `parse_from_date`
- [x] API `/api/schedule` POST сохраняет `parse_depth` и `parse_from_date`
- [x] API `/api/schedule/logs` возвращает `run_type` для каждой записи
- [x] `run_parser_task()` логирует запуски с `run_type` в БД

### Frontend HTML ✅
- [x] UI для выбора глубины парсинга (select с today/3days/from_date)
- [x] Date picker для выбора даты начала (`parseFromDate`)
- [x] Колонка "Тип" добавлена в таблицу истории запусков
- [x] Заголовок изменен с "История автозапусков" на "История запусков"

---

## Что нужно доделать в JavaScript (web/static/app.js):

### 1. Функция `loadScheduleLogs()` (примерно строки 169-222)

**Что изменить:**
Добавить колонку с типом запуска в таблицу.

**Текущий код формирует строки таблицы:**
```javascript
row.innerHTML = `
    <td class="timestamp">${formattedDate}</td>
    <td class="status ${statusClass}">${statusText}</td>
    <td>${log.images_parsed || 0}</td>
    <td>${log.images_analyzed || 0}</td>
    <td>${details}</td>
`;
```

**Нужно изменить на:**
```javascript
// Определяем тип запуска
const runType = log.run_type || 'auto';
const runTypeText = runType === 'manual' ? '🖱️ Ручной' : '⏰ Авто';

row.innerHTML = `
    <td class="timestamp">${formattedDate}</td>
    <td class="run-type">${runTypeText}</td>
    <td class="status ${statusClass}">${statusText}</td>
    <td>${log.images_parsed || 0}</td>
    <td>${log.images_analyzed || 0}</td>
    <td>${details}</td>
`;
```

---

### 2. Функция `loadSchedule()` (примерно строки 228-260)

**Что изменить:**
Загружать настройки `parse_depth` и `parse_from_date` из API.

**Добавить после строки с `document.getElementById('scheduleEndDate').value = ...`:**

```javascript
// Загружаем настройки глубины парсинга
const parseDepth = data.parse_depth || 'today';
const parseFromDate = data.parse_from_date || '';

document.getElementById('parseDepth').value = parseDepth;
if (parseFromDate) {
    document.getElementById('parseFromDate').value = parseFromDate;
}

// Показываем/скрываем date picker в зависимости от выбранной глубины
document.getElementById('parseFromDateGroup').style.display = 
    parseDepth === 'from_date' ? 'block' : 'none';
```

---

### 3. Функция `saveSchedule()` (примерно строки 441-492)

**Что изменить:**
Сохранять настройки `parse_depth` и `parse_from_date` в API.

**Найти где создается объект `scheduleData`:**
```javascript
const scheduleData = {
    enabled: document.getElementById('scheduleEnabled').checked,
    frequency: document.getElementById('scheduleFrequency').value,
    time: document.getElementById('scheduleTime').value,
    days: selectedDays,
    end_type: endType,
    end_date: endDate
};
```

**Добавить перед закрывающей скобкой }:**
```javascript
    end_date: endDate,
    parse_depth: document.getElementById('parseDepth').value,
    parse_from_date: document.getElementById('parseFromDate').value || ''
};
```

---

### 4. Event Listener для `parseDepth` (добавить новый код)

**Где добавить:**
В секцию с инициализацией event listeners (примерно строки 1010-1050)

**Код для добавления:**
```javascript
// Обработчик изменения глубины парсинга
document.getElementById('parseDepth').addEventListener('change', function() {
    const parseDepth = this.value;
    const parseFromDateGroup = document.getElementById('parseFromDateGroup');
    
    // Показываем date picker только для варианта "from_date"
    parseFromDateGroup.style.display = parseDepth === 'from_date' ? 'block' : 'none';
    
    // Если выбран другой вариант, очищаем дату
    if (parseDepth !== 'from_date') {
        document.getElementById('parseFromDate').value = '';
    }
});
```

---

### 5. Обновить scheduler/scheduler.py

**Файл:** `scheduler/scheduler.py`
**Функция:** `scheduled_task()` (примерно строки 80-120)

**Найти:**
```python
asyncio.run(run_parser_task())
```

**Заменить на:**
```python
asyncio.run(run_parser_task(run_type='auto'))
```

Это нужно чтобы автоматические запуски логировались с типом 'auto'.

---

## Проверка работоспособности:

### 1. Проверка глубины парсинга:
1. Открыть настройки → вкладка "Планировщик"
2. Изменить "Глубину парсинга"
3. При выборе "С определенной даты" - должен появиться date picker
4. Сохранить настройки
5. Запустить парсер вручную
6. Проверить что парсер использует нужную глубину (смотреть в логах)

### 2. Проверка типа запуска:
1. Открыть вкладку "Логи"
2. Запустить парсер вручную → в истории должно быть "🖱️ Ручной"
3. Включить планировщик и дождаться автозапуска → должно быть "⏰ Авто"

### 3. Проверка сохранения:
1. Установить все настройки планировщика
2. Закрыть настройки
3. Открыть снова → все настройки должны сохраниться

---

## Дополнительные стили CSS (опционально)

Добавить в `web/static/style.css`:

```css
/* Стиль для колонки типа запуска */
.schedule-logs-table .run-type {
    white-space: nowrap;
    font-size: 13px;
}

/* Группа date picker для глубины парсинга */
#parseFromDateGroup {
    margin-top: 10px;
    padding-left: 20px;
    border-left: 2px solid var(--accent-color);
}
```

---

## Итоговая статистика:

**Выполнено:** 15 из 20 задач (75%)

**Осталось:**
- 4 изменения в JavaScript (30 минут работы)
- 1 изменение в scheduler.py (5 минут)

**Оценка времени:** ~40 минут на финализацию
