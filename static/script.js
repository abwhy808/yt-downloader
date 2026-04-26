let selectedFormat = null;

// Elements
const videoUrlInput = document.getElementById('videoUrl');
const loadBtn = document.getElementById('loadBtn');
const errorMsg = document.getElementById('errorMsg');
const videoInfoSection = document.getElementById('videoInfo');
const formatsSection = document.getElementById('formatsSection');
const formatsList = document.getElementById('formatsList');
const downloadBtn = document.getElementById('downloadBtn');
const downloadStatus = document.getElementById('downloadStatus');
const downloadsList = document.getElementById('downloadsList');

// Event listeners
loadBtn.addEventListener('click', loadVideoInfo);
videoUrlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loadVideoInfo();
});

downloadBtn.addEventListener('click', downloadVideo);

// Load initial downloads list
loadDownloads();
setInterval(loadDownloads, 5000); // Обновлять каждые 5 секунд

async function loadVideoInfo() {
    const url = videoUrlInput.value.trim();

    if (!url) {
        showError('Пожалуйста, введите URL видео');
        return;
    }

    loadBtn.disabled = true;
    loadBtn.textContent = 'Загрузка...';
    errorMsg.style.display = 'none';

    try {
        const response = await fetch('/api/get-formats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Ошибка при загрузке информации');
        }

        const data = await response.json();

        // Отобразить информацию о видео
        document.getElementById('videoTitle').textContent = data.title;
        document.getElementById('thumbnail').src = data.thumbnail;
        document.getElementById('duration').textContent = formatDuration(data.duration);

        videoInfoSection.style.display = 'block';

        // Отобразить форматы
        displayFormats(data.formats);
        formatsSection.style.display = 'block';

        errorMsg.style.display = 'none';
    } catch (error) {
        showError(error.message);
    } finally {
        loadBtn.disabled = false;
        loadBtn.textContent = 'Загрузить информацию';
    }
}

function displayFormats(formats) {
    formatsList.innerHTML = '';
    selectedFormat = null;
    downloadBtn.style.display = 'none';

    if (formats.length === 0) {
        formatsList.innerHTML = '<p>Не найдены доступные форматы</p>';
        return;
    }

    // Сортировать по качеству (высокое первым)
    formats.sort((a, b) => {
        const heightA = parseInt(a.quality) || 0;
        const heightB = parseInt(b.quality) || 0;
        return heightB - heightA;
    });

    formats.forEach((format, index) => {
        const card = document.createElement('div');
        card.className = 'format-card';
        card.innerHTML = `
            <div class="format-quality">${format.quality}</div>
            <div class="format-ext">${format.ext.toUpperCase()}</div>
            <div class="format-size">${formatFileSize(format.filesize)}</div>
        `;

        card.addEventListener('click', () => {
            // Убрать предыдущее выделение
            document.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));

            // Выделить новый формат
            card.classList.add('selected');
            selectedFormat = format;
            downloadBtn.style.display = 'block';
        });

        formatsList.appendChild(card);
    });
}

async function downloadVideo() {
    if (!selectedFormat) {
        showError('Пожалуйста, выберите качество видео');
        return;
    }

    const url = videoUrlInput.value.trim();

    downloadBtn.disabled = true;
    downloadBtn.textContent = 'Скачивание...';
    downloadStatus.style.display = 'block';
    downloadStatus.className = 'download-status';
    downloadStatus.textContent = 'Скачивание видео, пожалуйста ждите...';

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                format_id: selectedFormat.format_id
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Ошибка при скачивании');
        }

        const data = await response.json();

        downloadStatus.className = 'download-status';
        downloadStatus.textContent = '✓ ' + data.message;

        // Обновить список скачанных видео
        await loadDownloads();

        // Очистить форму через 2 секунды
        setTimeout(() => {
            videoUrlInput.value = '';
            videoInfoSection.style.display = 'none';
            formatsSection.style.display = 'none';
            downloadStatus.style.display = 'none';
        }, 2000);

    } catch (error) {
        downloadStatus.className = 'download-status error';
        downloadStatus.textContent = '✗ ' + error.message;
    } finally {
        downloadBtn.disabled = false;
        downloadBtn.textContent = 'Скачать видео';
    }
}

async function loadDownloads() {
    try {
        const response = await fetch('/api/downloads');
        const downloads = await response.json();

        if (downloads.length === 0) {
            downloadsList.innerHTML = '<p class="loading">Нет скачанных видео</p>';
            return;
        }

        downloadsList.innerHTML = '';
        downloads.forEach(file => {
            const item = document.createElement('div');
            item.className = 'download-item';

            const date = new Date(file.modified);
            const dateStr = date.toLocaleString('ru-RU');

            item.innerHTML = `
                <div class="download-name">${file.name}</div>
                <div class="download-size">${formatFileSize(file.size)}</div>
                <div class="download-date">${dateStr}</div>
            `;

            downloadsList.appendChild(item);
        });
    } catch (error) {
        console.error('Ошибка при загрузке списка:', error);
    }
}

function showError(message) {
    errorMsg.textContent = message;
    errorMsg.style.display = 'block';
}

function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
}

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return 'Неизвестно';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
