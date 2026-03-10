// Глобальное состояние
let state = {
    creatives: [],
    offset: 0,
    limit: 50,
    selectedChannel: null,
    hasMore: true,
    selectedCreativeId: null
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadCreatives();
    initEventListeners();
    
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
}

// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        document.getElementById('statPosts').textContent = data.total_posts;
        document.getElementById('statImages').textContent = data.total_images;
        document.getElementById('statAnalyzed').textContent = data.total_analyzed;
        
        // Обновляем список каналов
        renderChannels(data.channels);
        
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
