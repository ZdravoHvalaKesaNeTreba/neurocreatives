// Глобальное состояние
let state = {
    creatives: [],
    offset: 0,
    limit: 50,
    selectedChannel: null,
    hasMore: true,
    selectedCreativeId: null,
    currentTab: 'gallery',  // 'gallery', 'table' или 'logs'
    tableOffset: 0,
    tableHasMore: true,
    tableData: [],  // Данные для таблицы
    filteredData: [],  // Отфильтрованные данные
    sortColumn: null,
    sortDirection: 'asc',
    filters: {
        channel: '',
        erMin: null,
        erMax: null,
        viewsMin: null,
        viewsMax: null
    },
    logs: {
        eventSource: null,
        paused: false,
        autoScroll: true,
        currentFilter: ''
    },
    scheduleLogs: {
        loaded: 0,  // Количество уже загруженных записей
        total: 0,   // Общее количество записей
        limit: 10   // Количество записей за один раз
    }
};

// ========== ПЛАНИРОВЩИК ==========

// Загрузка настроек планировщика
async function loadScheduleSettings() {
    try {
        const response = await fetch('/api/schedule');
        const data = await response.json();
        
        // Заполняем форму
        document.getElementById('scheduleEnabled').checked = data.enabled || false;
        document.getElementById('scheduleFrequency').value = data.frequency || 'daily';
        document.getElementById('scheduleTime').value = data.time || '08:00';
        
        // Дни недели для custom
        if (data.days && Array.isArray(data.days)) {
            document.querySelectorAll('.schedule-day').forEach(checkbox => {
                checkbox.checked = data.days.includes(parseInt(checkbox.value));
            });
        }
        
        // Срок действия
        const endType = data.end_type || 'indefinite';
        document.querySelector(`input[name="scheduleEndType"][value="${endType}"]`).checked = true;
        if (data.end_date) {
            document.getElementById('scheduleEndDate').value = data.end_date;
        }
        
        // Глубина парсинга
        const parseDepth = data.parse_depth || 'today';
        const parseFromDate = data.parse_from_date || '';
        document.getElementById('parseDepth').value = parseDepth;
        if (parseFromDate) {
            document.getElementById('parseFromDate').value = parseFromDate;
        }
        document.getElementById('parseFromDateGroup').style.display =
            parseDepth === 'from_date' ? 'block' : 'none';
        
        // Обновляем UI
        updateScheduleUI();
        updateScheduleStatus(data);
        
    } catch (error) {
        console.error('Ошибка при загрузке настроек планировщика:', error);
    }
}

// Обновление статуса планировщика
function updateScheduleStatus(data) {
    const statusBadge = document.getElementById('schedulerStatus');
    const nextRunInfo = document.getElementById('nextRunInfo');
    const nextRunTime = document.getElementById('nextRunTime');
    
    if (data.scheduler_running && data.enabled) {
        statusBadge.textContent = 'Запущен';
        statusBadge.classList.add('active');
        
        if (data.next_run) {
            const nextRun = new Date(data.next_run);
            nextRunTime.textContent = nextRun.toLocaleString('ru-RU');
            nextRunInfo.style.display = 'block';
        } else {
            nextRunInfo.style.display = 'none';
        }
    } else {
        statusBadge.textContent = 'Не запущен';
        statusBadge.classList.remove('active');
        nextRunInfo.style.display = 'none';
    }
}

// Обновление UI планировщика
function updateScheduleUI() {
    const enabled = document.getElementById('scheduleEnabled').checked;
    const frequency = document.getElementById('scheduleFrequency').value;
    const endType = document.querySelector('input[name="scheduleEndType"]:checked').value;
    
    // Включение/выключение настроек
    const scheduleSettings = document.getElementById('scheduleSettings');
    if (enabled) {
        scheduleSettings.classList.add('enabled');
    } else {
        scheduleSettings.classList.remove('enabled');
    }
    
    // Показ/скрытие custom дней
    const customDaysGroup = document.getElementById('customDaysGroup');
    if (frequency === 'custom') {
        customDaysGroup.style.display = 'block';
    } else {
        customDaysGroup.style.display = 'none';
    }
    
    // Показ/скрытие даты окончания
    const endDateGroup = document.getElementById('endDateGroup');
    if (endType === 'until_date') {
        endDateGroup.style.display = 'block';
    } else {
        endDateGroup.style.display = 'none';
    }
}

// Сохранение настроек планировщика
async function saveScheduleSettings() {
    const enabled = document.getElementById('scheduleEnabled').checked;
    const frequency = document.getElementById('scheduleFrequency').value;
    const time = document.getElementById('scheduleTime').value;
    const endType = document.querySelector('input[name="scheduleEndType"]:checked').value;
    const endDate = document.getElementById('scheduleEndDate').value;
    
    // Собираем выбранные дни недели
    const days = [];
    document.querySelectorAll('.schedule-day:checked').forEach(checkbox => {
        days.push(parseInt(checkbox.value));
    });
    
    const data = {
        enabled,
        frequency,
        time,
        days,
        end_type: endType,
        end_date: endDate || null,
        parse_depth: document.getElementById('parseDepth').value,
        parse_from_date: document.getElementById('parseFromDate').value || ''
    };
    
    try {
        const response = await fetch('/api/schedule', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Настройки планировщика сохранены');
            // Перезагружаем настройки для обновления статуса
            setTimeout(() => loadScheduleSettings(), 500);
        } else {
            alert('Ошибка: ' + (result.detail || 'Не удалось сохранить'));
        }
    } catch (error) {
        console.error('Ошибка при сохранении настроек планировщика:', error);
        alert('Ошибка сохранения настроек');
    }
}

// Загрузка логов планировщика
async function loadScheduleLogs(loadMore = false) {
    try {
        const limit = loadMore ? state.scheduleLogs.limit : 10;
        const offset = loadMore ? state.scheduleLogs.loaded : 0;
        
        const response = await fetch(`/api/schedule/logs?limit=${limit}&offset=${offset}`);
        const data = await response.json();
        
        const tbody = document.getElementById('scheduleLogsBody');
        const loadMoreBtn = document.getElementById('scheduleLogsLoadMore');
        
        // Обновляем состояние
        if (!loadMore) {
            state.scheduleLogs.loaded = 0;
        }
        
        if (data.logs && data.logs.length > 0) {
            const rows = data.logs.map(log => {
                const timestamp = new Date(log.timestamp).toLocaleString('ru-RU');
                const statusClass = log.status === 'success' ? 'success' : 'error';
                const statusText = log.status === 'success' ? 'Успешно' : 'Ошибка';
                const runType = log.run_type || 'auto';
                const runTypeText = runType === 'manual' ? '🖱️ Ручной' : '⏰ Авто';
                
                return `
                    <tr>
                        <td>${timestamp}</td>
                        <td>${runTypeText}</td>
                        <td><span class="log-status ${statusClass}">${statusText}</span></td>
                        <td>${log.images_parsed || 0}</td>
                        <td>${log.images_analyzed || 0}</td>
                        <td class="log-details">${log.error_message || '—'}</td>
                    </tr>
                `;
            }).join('');
            
            if (loadMore) {
                tbody.innerHTML += rows;
            } else {
                tbody.innerHTML = rows;
            }
            
            state.scheduleLogs.loaded += data.logs.length;
            state.scheduleLogs.total = data.count || data.logs.length;
            
            // Показываем/скрываем кнопку "Показать еще"
            if (state.scheduleLogs.loaded < state.scheduleLogs.total) {
                loadMoreBtn.style.display = 'block';
            } else {
                loadMoreBtn.style.display = 'none';
            }
        } else {
            if (!loadMore) {
                tbody.innerHTML = '<tr><td colspan="6" class="no-data">Нет данных о запусках</td></tr>';
            }
            loadMoreBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Ошибка при загрузке логов планировщика:', error);
    }
}

// Загрузка дополнительных логов планировщика
function loadMoreScheduleLogs() {
    loadScheduleLogs(true);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadCreatives();
    initEventListeners();
    initTabSwitching();
    
    // Обновляем статистику каждые 5 секунд
    setInterval(loadStats, 5000);
});

// Инициализация обработчиков событий
function initEventListeners() {
    document.getElementById('btnRunParser').addEventListener('click', runParser);
    document.getElementById('btnRunAnalysis').addEventListener('click', runAnalysis);
    document.getElementById('btnRefresh').addEventListener('click', refreshCreatives);
    document.getElementById('btnLoadMore').addEventListener('click', loadMoreCreatives);
    document.getElementById('btnCloseDetail').addEventListener('click', closeDetailPanel);
    
    // Кнопки таблицы
    document.getElementById('btnRefreshTable').addEventListener('click', refreshTable);
    document.getElementById('btnLoadMoreTable').addEventListener('click', loadMoreTable);
    
    // Кнопки фильтров
    document.getElementById('btnApplyFilters').addEventListener('click', applyFilters);
    document.getElementById('btnResetFilters').addEventListener('click', resetFilters);
    
    // Модальное окно настроек
    document.getElementById('btnSettings').addEventListener('click', openSettingsModal);
    document.getElementById('btnCloseSettingsModal').addEventListener('click', closeSettingsModal);
    document.getElementById('btnCancelSettings').addEventListener('click', closeSettingsModal);
    document.getElementById('btnSaveSettings').addEventListener('click', saveSettings);
    
    // Обработчики для планировщика
    document.getElementById('scheduleEnabled').addEventListener('change', updateScheduleUI);
    document.getElementById('scheduleFrequency').addEventListener('change', updateScheduleUI);
    document.querySelectorAll('input[name="scheduleEndType"]').forEach(radio => {
        radio.addEventListener('change', updateScheduleUI);
    });
    document.getElementById('parseDepth').addEventListener('change', function() {
        const parseDepth = this.value;
        const parseFromDateGroup = document.getElementById('parseFromDateGroup');
        parseFromDateGroup.style.display = parseDepth === 'from_date' ? 'block' : 'none';
        if (parseDepth !== 'from_date') {
            document.getElementById('parseFromDate').value = '';
        }
    });
    document.getElementById('btnRefreshScheduleLogs').addEventListener('click', () => loadScheduleLogs(false));
    document.getElementById('btnLoadMoreScheduleLogs').addEventListener('click', loadMoreScheduleLogs);
    
    // Закрытие модального окна по клику на фон
    document.getElementById('settingsModal').addEventListener('click', (e) => {
        if (e.target.id === 'settingsModal') {
            closeSettingsModal();
        }
    });
    
    // Закрытие детальной панели по клику на фон (backdrop)
    document.getElementById('detailPanel').addEventListener('click', (e) => {
        // Закрываем если клик был по самому overlay (класс detail-panel), а не по его дочерним элементам
        if (e.target.classList.contains('detail-panel')) {
            closeDetailPanel();
        }
    });
    
    // Обновление счетчика каналов при вводе
    document.getElementById('channelsTextarea').addEventListener('input', updateChannelsCount);
    
    // Переключение вкладок в настройках
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            switchSettingsTab(e.target.dataset.tab);
        });
    });
    
    // Показать/скрыть API ключ
    document.getElementById('btnToggleApiKey').addEventListener('click', toggleApiKeyVisibility);
    
    // Telegram API Hash: показать/скрыть
    document.getElementById('btnToggleTgApiHash').addEventListener('click', toggleTgApiHashVisibility);
    
    // Сброс сессии Telegram
    document.getElementById('btnResetTgSession').addEventListener('click', resetTgSession);
    
    // Логи
    document.getElementById('btnPauseLogs').addEventListener('click', toggleLogsPause);
    document.getElementById('btnClearLogs').addEventListener('click', clearLogs);
    document.getElementById('logLevelFilter').addEventListener('change', filterLogs);
}

// Инициализация переключения вкладок
function initTabSwitching() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

// Переключение вкладок
function switchTab(tabName) {
    state.currentTab = tabName;
    
    // Обновляем активные классы на вкладках
    document.querySelectorAll('.tab').forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Переключаем видимость контейнеров
    const galleryView = document.getElementById('galleryView');
    const tableView = document.getElementById('tableView');
    const logsView = document.getElementById('logsView');
    const guideView = document.getElementById('guideView');
    
    if (tabName === 'gallery') {
        galleryView.classList.add('active');
        tableView.classList.remove('active');
        logsView.classList.remove('active');
        if (guideView) guideView.classList.remove('active');
    } else if (tabName === 'table') {
        galleryView.classList.remove('active');
        tableView.classList.add('active');
        logsView.classList.remove('active');
        if (guideView) guideView.classList.remove('active');
        // Загружаем данные для таблицы, если еще не загружены
        if (document.getElementById('tableBody').children.length === 1) {
            loadTable();
        }
    } else if (tabName === 'logs') {
        galleryView.classList.remove('active');
        tableView.classList.remove('active');
        logsView.classList.add('active');
        if (guideView) guideView.classList.remove('active');
        // Загружаем логи планировщика
        loadScheduleLogs();
        // Инициализируем SSE для логов, если еще не инициализировано
        if (!state.logs.eventSource) {
            initLogsStream();
        }
    } else if (tabName === 'guide') {
        galleryView.classList.remove('active');
        tableView.classList.remove('active');
        logsView.classList.remove('active');
        if (guideView) guideView.classList.add('active');
    }
}

// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        // Обновляем статистику в сайдбаре
        document.getElementById('statPosts').textContent = data.total_posts;
        document.getElementById('statImages').textContent = data.total_images;
        document.getElementById('statAnalyzed').textContent = data.total_analyzed;
        
        // Обновляем статистику в заголовке вкладок
        document.getElementById('headerStatPosts').textContent = data.total_posts;
        document.getElementById('headerStatImages').textContent = data.total_images;
        document.getElementById('headerStatAnalyzed').textContent = data.total_analyzed;
        
        // Обновляем средние значения под фильтрами
        if (data.avg_er !== undefined) {
            document.getElementById('avgER').textContent = data.avg_er + '%';
        }
        if (data.avg_views !== undefined) {
            document.getElementById('avgViews').textContent = formatNumber(data.avg_views);
        }
        
        // Обновляем список каналов
        renderChannels(data.channels);
        
        // Обновляем выпадающий список каналов для фильтра
        updateChannelsFilter(data.channels);
        
        // Обновляем статусы
        updateStatus('parser', data.parser_status);
        updateStatus('analysis', data.analysis_status);
        
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

// Отрисовка списка каналов
function renderChannels(channels) {
    const container = document.getElementById('channelsList');
    
    if (!channels || channels.length === 0) {
        container.innerHTML = '<div class="loading">Нет каналов</div>';
        return;
    }
    
    container.innerHTML = channels.map(channel => `
        <div class="channel-item ${state.selectedChannel === channel ? 'active' : ''}"
             onclick="filterByChannel('${channel}')">
            ${channel}
        </div>
    `).join('');
}

// Обновление выпадающего списка каналов для фильтра
function updateChannelsFilter(channels) {
    const select = document.getElementById('filterChannel');
    const currentValue = select.value;
    
    // Очищаем и заполняем заново
    select.innerHTML = '<option value="">Все каналы</option>';
    
    if (channels && channels.length > 0) {
        channels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel;
            option.textContent = channel;
            select.appendChild(option);
        });
    }
    
    // Восстанавливаем выбранное значение если оно было
    if (currentValue) {
        select.value = currentValue;
    }
}

// Обновление статусов задач
function updateStatus(type, status) {
    const elementId = type === 'parser' ? 'parserStatus' : 'analysisStatus';
    const element = document.getElementById(elementId);
    
    if (status.running) {
        element.textContent = '⏳ ' + status.message;
        element.style.color = 'var(--color-accent)';
    } else {
        element.textContent = status.message;
        element.style.color = 'var(--color-text-secondary)';
    }
}

// Загрузка креативов
async function loadCreatives(append = false) {
    try {
        const params = new URLSearchParams({
            limit: state.limit,
            offset: append ? state.offset : 0
        });
        
        if (state.selectedChannel) {
            params.append('channel', state.selectedChannel);
        }
        
        const response = await fetch(`/api/creatives?${params}`);
        const data = await response.json();
        
        if (append) {
            state.creatives = [...state.creatives, ...data.creatives];
        } else {
            state.creatives = data.creatives;
            state.offset = 0;
        }
        
        state.offset += data.creatives.length;
        state.hasMore = state.offset < data.total;
        
        renderCreatives();
        
    } catch (error) {
        console.error('Ошибка загрузки креативов:', error);
        document.getElementById('creativesGrid').innerHTML = `
            <div class="loading">Ошибка загрузки креативов</div>
        `;
    }
}

// Отрисовка креативов
function renderCreatives() {
    const container = document.getElementById('creativesGrid');
    
    if (state.creatives.length === 0) {
        container.innerHTML = '<div class="loading">Креативов пока нет. Запустите парсер.</div>';
        document.getElementById('loadMoreContainer').style.display = 'none';
        return;
    }
    
    container.innerHTML = state.creatives.map(creative => {
        const emotion = creative.analysis?.emotion || '';
        const er = creative.er || 0;
        const imagePath = creative.image?.file_path || '';
        
        return `
            <div class="creative-card" onclick="openCreativeDetail(${creative.id})">
                <img src="/${imagePath}" alt="${creative.channel}" class="creative-image" 
                     onerror="this.src='/static/placeholder.png'">
                <div class="creative-content">
                    <div class="creative-channel">${creative.channel}</div>
                    <div class="creative-text">${truncateText(creative.text, 100)}</div>
                    <div class="creative-meta">
                        <div class="meta-item">
                            <span class="meta-label">ER</span>
                            <span class="meta-value">${er}%</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Просмотров</span>
                            <span class="meta-value">${formatNumber(creative.views)}</span>
                        </div>
                    </div>
                    ${emotion ? `
                        <div class="creative-tags">
                            <span class="tag">${emotion}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    // Показываем кнопку "Загрузить еще"
    const loadMoreContainer = document.getElementById('loadMoreContainer');
    loadMoreContainer.style.display = state.hasMore ? 'block' : 'none';
}

// Открытие детальной панели
async function openCreativeDetail(creativeId) {
    try {
        const response = await fetch(`/api/creative/${creativeId}`);
        const creative = await response.json();
        
        state.selectedCreativeId = creativeId;
        
        const panel = document.getElementById('detailPanel');
        const content = document.getElementById('detailContent');
        
        const image = creative.images[0];
        const analysis = image?.analysis;
        
        content.innerHTML = `
            <img src="/${image.file_path}" alt="${creative.channel}" class="detail-image"
                 onerror="this.src='/static/placeholder.png'">
            
            <div class="detail-section">
                <div class="detail-title">Информация</div>
                <div class="detail-field">
                    <div class="detail-field-label">Канал</div>
                    <div class="detail-field-value">${creative.channel}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Дата публикации</div>
                    <div class="detail-field-value">${formatDate(creative.date)}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Ссылка на пост</div>
                    <div class="detail-field-value">
                        <a href="${creative.post_url}" target="_blank" class="detail-link">
                            Открыть в Telegram
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <div class="detail-title">Текст поста</div>
                <div class="detail-field-value">${creative.text}</div>
            </div>
            
            <div class="detail-section">
                <div class="detail-title">Статистика</div>
                <div class="detail-field">
                    <div class="detail-field-label">Просмотров</div>
                    <div class="detail-field-value">${formatNumber(creative.views)}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Пересылок</div>
                    <div class="detail-field-value">${formatNumber(creative.forwards)}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Комментариев</div>
                    <div class="detail-field-value">${formatNumber(creative.replies)}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Реакций</div>
                    <div class="detail-field-value">${formatNumber(creative.reactions)}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Engagement Rate</div>
                    <div class="detail-field-value">${creative.er}%</div>
                </div>
            </div>
            
            ${analysis ? `
                <div class="detail-section">
                    <div class="detail-title">AI Анализ</div>
                    <div class="detail-field">
                        <div class="detail-field-label">Тип креатива</div>
                        <div class="detail-field-value">${analysis.creative_type}</div>
                    </div>
                    <div class="detail-field">
                        <div class="detail-field-label">Сцена</div>
                        <div class="detail-field-value">${analysis.scene}</div>
                    </div>
                    <div class="detail-field">
                        <div class="detail-field-label">Объекты</div>
                        <div class="detail-field-value">${analysis.objects}</div>
                    </div>
                    <div class="detail-field">
                        <div class="detail-field-label">Эмоция</div>
                        <div class="detail-field-value">${analysis.emotion}</div>
                    </div>
                    <div class="detail-field">
                        <div class="detail-field-label">Текст присутствует</div>
                        <div class="detail-field-value">${analysis.text_present}</div>
                    </div>
                    <div class="detail-field">
                        <div class="detail-field-label">Визуальная сила</div>
                        <div class="detail-field-value">${analysis.visual_strength_score}/10</div>
                    </div>
                </div>
            ` : '<div class="detail-section"><div class="loading">Анализ еще не выполнен</div></div>'}
        `;
        
        panel.classList.add('open');
        
    } catch (error) {
        console.error('Ошибка загрузки деталей:', error);
    }
}

// Закрытие детальной панели
function closeDetailPanel() {
    const panel = document.getElementById('detailPanel');
    panel.classList.remove('open');
    state.selectedCreativeId = null;
}

// Фильтрация по каналу
function filterByChannel(channel) {
    if (state.selectedChannel === channel) {
        state.selectedChannel = null;
    } else {
        state.selectedChannel = channel;
    }
    
    loadCreatives();
    loadStats(); // Обновляем UI каналов
}

// Обновление креативов
function refreshCreatives() {
    state.offset = 0;
    loadCreatives();
}

// Загрузка дополнительных креативов
function loadMoreCreatives() {
    loadCreatives(true);
}

// Запуск парсера
async function runParser() {
    const btn = document.getElementById('btnRunParser');
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/run-parser', { method: 'POST' });
        const data = await response.json();
        
        alert(data.message);
        
        // Обновляем данные через 2 секунды
        setTimeout(() => {
            loadStats();
            refreshCreatives();
        }, 2000);
        
    } catch (error) {
        console.error('Ошибка запуска парсера:', error);
        alert('Ошибка запуска парсера');
    } finally {
        setTimeout(() => {
            btn.disabled = false;
        }, 3000);
    }
}

// Запуск анализа
async function runAnalysis() {
    const btn = document.getElementById('btnRunAnalysis');
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/run-analysis', { method: 'POST' });
        const data = await response.json();
        
        alert(data.message);
        
        // Обновляем данные через 2 секунды
        setTimeout(() => {
            loadStats();
            refreshCreatives();
        }, 2000);
        
    } catch (error) {
        console.error('Ошибка запуска анализа:', error);
        alert('Ошибка запуска анализа');
    } finally {
        setTimeout(() => {
            btn.disabled = false;
        }, 3000);
    }
}

// Утилиты
function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function formatNumber(num) {
    if (!num) return '0';
    return num.toLocaleString('ru-RU');
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Модальное окно настроек
async function openSettingsModal() {
    try {
        // Загружаем список каналов
        const channelsResponse = await fetch('/api/channels');
        const channelsData = await channelsResponse.json();
        
        const channelsTextarea = document.getElementById('channelsTextarea');
        channelsTextarea.value = channelsData.channels.join('\n');
        updateChannelsCount();
        
        // Загружаем настройки
        const settingsResponse = await fetch('/api/settings');
        const settingsData = await settingsResponse.json();
        
        // Заполняем поля настроек
        document.getElementById('apiKeyInput').value = settingsData.openai_api_key || '';
        document.getElementById('promptTextarea').value = settingsData.analysis_prompt || 'Что на этом фото?';
        document.getElementById('telegramApiIdInput').value = settingsData.telegram_api_id || '';
        document.getElementById('telegramApiHashInput').value = settingsData.telegram_api_hash || '';
        
        const modal = document.getElementById('settingsModal');
        modal.classList.add('open');
        
        // Загружаем настройки планировщика
        loadScheduleSettings();
        
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
        alert('Ошибка загрузки настроек');
    }
}

function closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    modal.classList.remove('open');
}

// Переключение вкладок настроек
function switchSettingsTab(tabName) {
    // Обновляем активные классы на вкладках
    document.querySelectorAll('.settings-tab').forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Переключаем видимость панелей
    document.querySelectorAll('.settings-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    const panels = {
        'channels': 'settingsChannels',
        'telegram': 'settingsTelegram',
        'api': 'settingsAPI',
        'prompt': 'settingsPrompt',
        'scheduler': 'settingsScheduler'
    };
    
    const activePanel = document.getElementById(panels[tabName]);
    if (activePanel) {
        activePanel.classList.add('active');
    }
}

// Показать/скрыть API ключ
function toggleApiKeyVisibility() {
    const input = document.getElementById('apiKeyInput');
    const btn = document.getElementById('btnToggleApiKey');
    
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈 Скрыть';
    } else {
        input.type = 'password';
        btn.textContent = '👁️ Показать';
    }
}

// Показать/скрыть Telegram API Hash
function toggleTgApiHashVisibility() {
    const input = document.getElementById('telegramApiHashInput');
    const btn = document.getElementById('btnToggleTgApiHash');
    
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈 Скрыть';
    } else {
        input.type = 'password';
        btn.textContent = '👁️ Показать';
    }
}

// Сброс сессии Telegram
async function resetTgSession() {
    if (!confirm('Вы уверены? Сессия Telegram будет удалена. После этого потребуется повторная авторизация при запуске парсера.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/telegram/reset-session', { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message || 'Сессия Telegram успешно сброшена');
        } else {
            alert('Ошибка: ' + (data.detail || 'Не удалось сбросить сессию'));
        }
    } catch (error) {
        console.error('Ошибка при сбросе сессии:', error);
        alert('Ошибка при сбросе сессии Telegram');
    }
}

async function saveSettings() {
    const btn = document.getElementById('btnSaveSettings');
    btn.disabled = true;
    btn.textContent = 'Сохранение...';
    
    try {
        // Определяем активную вкладку
        const activeTab = document.querySelector('.settings-tab.active').dataset.tab;
        
        // Если активна вкладка планировщика, сохраняем настройки планировщика
        if (activeTab === 'scheduler') {
            await saveScheduleSettings();
            btn.disabled = false;
            btn.textContent = 'Сохранить';
            return;
        }
        
        // Сохраняем каналы
        const channelsText = document.getElementById('channelsTextarea').value.trim();
        const channels = channelsText
            .split('\n')
            .map(ch => ch.trim())
            .filter(ch => ch.length > 0);
        
        if (channels.length > 0) {
            const channelsResponse = await fetch('/api/channels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(channels)
            });
            
            if (!channelsResponse.ok) {
                throw new Error('Ошибка сохранения каналов');
            }
        }
        
        // Сохраняем настройки
        const settings = {
            openai_api_key: document.getElementById('apiKeyInput').value.trim(),
            analysis_prompt: document.getElementById('promptTextarea').value.trim(),
            telegram_api_id: document.getElementById('telegramApiIdInput').value.trim(),
            telegram_api_hash: document.getElementById('telegramApiHashInput').value.trim()
        };
        
        const settingsResponse = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        const settingsData = await settingsResponse.json();
        
        if (settingsResponse.ok) {
            alert('Настройки успешно сохранены');
            closeSettingsModal();
            loadStats(); // Обновляем список каналов в сайдбаре
        } else {
            alert(`Ошибка: ${settingsData.detail}`);
        }
        
    } catch (error) {
        console.error('Ошибка сохранения настроек:', error);
        alert('Ошибка сохранения настроек');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Сохранить';
    }
}

function updateChannelsCount() {
    const textarea = document.getElementById('channelsTextarea');
    const channelsText = textarea.value.trim();
    
    const channels = channelsText
        .split('\n')
        .map(ch => ch.trim())
        .filter(ch => ch.length > 0);
    
    const countElement = document.getElementById('channelsCount');
    countElement.textContent = channels.length;
}

// ========== ТАБЛИЧНОЕ ПРЕДСТАВЛЕНИЕ ==========

// Загрузка данных для таблицы
async function loadTable(append = false) {
    try {
        const params = new URLSearchParams({
            limit: state.limit,
            offset: append ? state.tableOffset : 0
        });
        
        const response = await fetch(`/api/creatives?${params}`);
        const data = await response.json();
        
        if (append) {
            state.tableData = [...state.tableData, ...data.creatives];
            state.tableOffset += data.creatives.length;
        } else {
            state.tableData = data.creatives;
            state.tableOffset = data.creatives.length;
        }
        
        state.tableHasMore = state.tableOffset < data.total;
        
        // Если активны фильтры, применяем их
        if (state.filters.channel || state.filters.erMin || state.filters.erMax || 
            state.filters.viewsMin || state.filters.viewsMax) {
            applyFilters();
        } else {
            renderTableRows(state.tableData, append);
        }
        
        // Показываем/скрываем кнопку "Загрузить еще"
        const loadMoreContainer = document.getElementById('loadMoreTableContainer');
        loadMoreContainer.style.display = state.tableHasMore ? 'block' : 'none';
        
    } catch (error) {
        console.error('Ошибка загрузки данных для таблицы:', error);
        document.getElementById('tableBody').innerHTML = `
            <tr><td colspan="8" class="loading">Ошибка загрузки данных</td></tr>
        `;
    }
}

// Отрисовка строк таблицы
function renderTableRows(creatives, append = false) {
    const tbody = document.getElementById('tableBody');
    
    if (!append) {
        tbody.innerHTML = '';
    }
    
    if (creatives.length === 0 && !append) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">Креативов пока нет</td></tr>';
        return;
    }
    
    creatives.forEach(creative => {
        const row = document.createElement('tr');
        row.style.cursor = 'pointer';
        
        const imagePath = creative.image?.file_path || '';
        const promptDescription = creative.analysis 
            ? generatePromptDescription(creative)
            : 'Анализ не выполнен';
        
        row.innerHTML = `
            <td class="table-cell-image">
                <img src="/${imagePath}" alt="${creative.channel}" 
                     onerror="this.src='/static/placeholder.png'">
            </td>
            <td class="table-cell-channel">${creative.channel}</td>
            <td class="table-cell-date">${formatDateShort(creative.date)}</td>
            <td class="table-cell-text">
                <div class="table-text-content">${creative.text || ''}</div>
            </td>
            <td class="table-cell-views">${formatNumber(creative.views)}</td>
            <td class="table-cell-er">${creative.er}%</td>
            <td class="table-cell-description">
                <div class="table-text-content">${promptDescription}</div>
            </td>
            <td class="table-cell-actions">
                <button class="btn-table-action" onclick="event.stopPropagation(); downloadImage('/${imagePath}', '${creative.channel}_${creative.id}')">
                    💾 Скачать
                </button>
                <button class="btn-table-action" onclick="event.stopPropagation(); copyPromptDescription(\`${promptDescription.replace(/`/g, '\\`')}\`)">
                    📋 Копировать
                </button>
            </td>
        `;
        
        // Добавляем обработчик клика на строку
        row.addEventListener('click', (e) => {
            // Проверяем, что клик не был по кнопкам действий
            if (!e.target.closest('.btn-table-action')) {
                openCreativeDetail(creative.id);
            }
        });
        
        tbody.appendChild(row);
    });
}

// Генерация текстового описания для промпта
function generatePromptDescription(creative) {
    const analysis = creative.analysis;
    if (!analysis) return 'Нет данных';
    
    const parts = [];
    
    if (analysis.creative_type) {
        parts.push(`Тип: ${analysis.creative_type}`);
    }
    
    if (analysis.scene) {
        parts.push(`Сцена: ${analysis.scene}`);
    }
    
    if (analysis.objects) {
        parts.push(`Объекты: ${analysis.objects}`);
    }
    
    if (analysis.emotion) {
        parts.push(`Эмоция: ${analysis.emotion}`);
    }
    
    if (analysis.text_present) {
        parts.push(`Текст: ${analysis.text_present}`);
    }
    
    return parts.join('. ');
}

// Скачивание изображения
async function downloadImage(imagePath, filename) {
    try {
        const response = await fetch(imagePath);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename}.jpg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Ошибка скачивания изображения:', error);
        alert('Ошибка скачивания изображения');
    }
}

// Копирование описания для промпта
async function copyPromptDescription(text) {
    try {
        await navigator.clipboard.writeText(text);
        
        // Показываем уведомление
        const notification = document.createElement('div');
        notification.className = 'copy-notification';
        notification.textContent = '✓ Скопировано в буфер обмена';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 2000);
        
    } catch (error) {
        console.error('Ошибка копирования:', error);
        alert('Ошибка копирования в буфер обмена');
    }
}

// Обновление таблицы
function refreshTable() {
    state.tableOffset = 0;
    loadTable();
}

// Загрузка дополнительных строк
function loadMoreTable() {
    loadTable(true);
}

// Форматирование даты (короткий вариант)
function formatDateShort(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Применение фильтров
function applyFilters() {
    // Читаем значения фильтров
    const channel = document.getElementById('filterChannel').value;
    const erMin = parseFloat(document.getElementById('filterERMin').value) || null;
    const erMax = parseFloat(document.getElementById('filterERMax').value) || null;
    const viewsMin = parseInt(document.getElementById('filterViewsMin').value) || null;
    const viewsMax = parseInt(document.getElementById('filterViewsMax').value) || null;
    
    // Сохраняем в state
    state.filters = { channel, erMin, erMax, viewsMin, viewsMax };
    
    // Фильтруем данные
    state.filteredData = state.tableData.filter(creative => {
        // Фильтр по каналу
        if (channel && creative.channel !== channel) {
            return false;
        }
        
        // Фильтр по ER
        const er = creative.er || 0;
        if (erMin !== null && er < erMin) {
            return false;
        }
        if (erMax !== null && er > erMax) {
            return false;
        }
        
        // Фильтр по просмотрам
        const views = creative.views || 0;
        if (viewsMin !== null && views < viewsMin) {
            return false;
        }
        if (viewsMax !== null && views > viewsMax) {
            return false;
        }
        
        return true;
    });
    
    // Перерисовываем таблицу с отфильтрованными данными
    renderTableRows(state.filteredData, false);
    
    // Скрываем кнопку "Загрузить еще" при активных фильтрах
    document.getElementById('loadMoreTableContainer').style.display = 'none';
}

// Сброс фильтров
function resetFilters() {
    // Очищаем поля фильтров
    document.getElementById('filterChannel').value = '';
    document.getElementById('filterERMin').value = '';
    document.getElementById('filterERMax').value = '';
    document.getElementById('filterViewsMin').value = '';
    document.getElementById('filterViewsMax').value = '';
    
    // Сбрасываем state
    state.filters = {
        channel: '',
        erMin: null,
        erMax: null,
        viewsMin: null,
        viewsMax: null
    };
    state.filteredData = [];
    
    // Показываем все данные
    renderTableRows(state.tableData, false);
    
    // Показываем кнопку "Загрузить еще" если есть еще данные
    document.getElementById('loadMoreTableContainer').style.display = state.tableHasMore ? 'block' : 'none';
}

// ========== ЛОГИ ==========

// Инициализация SSE потока логов
function initLogsStream() {
    // Закрываем предыдущее соединение, если есть
    if (state.logs.eventSource) {
        state.logs.eventSource.close();
    }
    
    // Создаем новое SSE соединение
    const eventSource = new EventSource('/api/logs/stream');
    state.logs.eventSource = eventSource;
    
    eventSource.onopen = () => {
        console.log('SSE соединение установлено');
    };
    
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Пропускаем служебные сообщения
            if (data.type === 'connected') {
                console.log(data.message);
                return;
            }
            
            // Добавляем лог, если не на паузе
            if (!state.logs.paused) {
                addLogEntry(data);
            }
        } catch (error) {
            console.error('Ошибка парсинга лога:', error);
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('Ошибка SSE соединения:', error);
        eventSource.close();
        
        // Пытаемся переподключиться через 5 секунд
        setTimeout(() => {
            if (state.currentTab === 'logs') {
                initLogsStream();
            }
        }, 5000);
    };
}

// Добавление записи лога
function addLogEntry(logData) {
    const logsContent = document.getElementById('logsContent');
    const currentFilter = state.logs.currentFilter;
    
    // Проверяем фильтр
    if (currentFilter && logData.level !== currentFilter) {
        return;
    }
    
    // Создаем элемент лога
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${logData.level.toLowerCase()}`;
    
    const timestamp = document.createElement('span');
    timestamp.className = 'log-timestamp';
    timestamp.textContent = `[${logData.timestamp}]`;
    
    const level = document.createElement('span');
    level.className = 'log-level';
    level.textContent = logData.level;
    
    const message = document.createElement('span');
    message.className = 'log-message';
    message.textContent = logData.message;
    
    logEntry.appendChild(timestamp);
    logEntry.appendChild(level);
    logEntry.appendChild(message);
    
    logsContent.appendChild(logEntry);
    
    // Автопрокрутка
    if (state.logs.autoScroll) {
        logsContent.scrollTop = logsContent.scrollHeight;
    }
}

// Переключение паузы логов
function toggleLogsPause() {
    state.logs.paused = !state.logs.paused;
    
    const btn = document.getElementById('btnPauseLogs');
    if (state.logs.paused) {
        btn.innerHTML = '<span class="btn-icon">▶️</span> Продолжить';
        state.logs.autoScroll = false;
    } else {
        btn.innerHTML = '<span class="btn-icon">⏸️</span> Пауза';
        state.logs.autoScroll = true;
    }
}

// Очистка логов
function clearLogs() {
    const logsContent = document.getElementById('logsContent');
    logsContent.innerHTML = '<div class="log-entry log-info">' +
        '<span class="log-timestamp">[--:--:--]</span>' +
        '<span class="log-level">INFO</span>' +
        '<span class="log-message">Логи очищены</span>' +
        '</div>';
}

// Фильтрация логов по уровню
function filterLogs() {
    const filter = document.getElementById('logLevelFilter').value;
    state.logs.currentFilter = filter;
    
    const logsContent = document.getElementById('logsContent');
    const allLogs = logsContent.querySelectorAll('.log-entry');
    
    allLogs.forEach(log => {
        if (!filter) {
            log.style.display = 'flex';
        } else {
            const level = log.querySelector('.log-level').textContent;
            log.style.display = level === filter ? 'flex' : 'none';
        }
    });
}
