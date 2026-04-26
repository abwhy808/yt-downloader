from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
from pathlib import Path
import json
from datetime import datetime
import logging
import subprocess
import sys

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Папка для сохранения видео
DOWNLOADS_FOLDER = Path('downloads')
DOWNLOADS_FOLDER.mkdir(exist_ok=True)

# User agents для обхода блокировок
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
]

def get_ydl_opts(format_id=None, download=False):
    """Получить оптимальные опции yt-dlp"""
    opts = {
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 60,
        'retries': 15,
        'fragment_retries': 15,
        'skip_unavailable_fragments': True,
        'http_headers': {
            'User-Agent': USER_AGENTS[0],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'tv'],
                'player_skip': ['webpage', 'config'],
            }
        },
        'age_limit': 18,
        'socket_timeout': 60,
    }
    
    if format_id:
        opts['format'] = format_id
        opts['outtmpl'] = str(DOWNLOADS_FOLDER / '%(title)s_[%(format_id)s].%(ext)s')
    
    if download:
        # Для скачивания добавим больше попыток
        opts['retries'] = 20
        opts['fragment_retries'] = 20
    
    return opts

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get-formats', methods=['POST'])
def get_formats():
    """Получить доступные форматы видео"""
    try:
        data = request.json
        url = data.get('url')
        
        logger.info(f"Запрос форматов для URL: {url}")
        
        if not url:
            return jsonify({'error': 'URL не указан'}), 400
        
        ydl_opts = get_ydl_opts()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Загрузка информации о видео...")
            info = ydl.extract_info(url, download=False)
            logger.info(f"Видео получено: {info.get('title')}")
            
            # Получить форматы с видео и аудио
            formats = {}
            for fmt in info.get('formats', []):
                vcodec = fmt.get('vcodec')
                acodec = fmt.get('acodec')
                
                # Ищем форматы с видео И аудио
                if vcodec != 'none' and acodec != 'none':
                    height = fmt.get('height', 0)
                    ext = fmt.get('ext', 'mp4')
                    format_id = fmt.get('format_id')
                    filesize = fmt.get('filesize', 0)
                    
                    quality_label = f"{height}p" if height else "Unknown"
                    key = f"{quality_label}_{ext}"
                    
                    if key not in formats or (filesize and filesize > (formats[key].get('filesize') or 0)):
                        formats[key] = {
                            'format_id': format_id,
                            'quality': quality_label,
                            'ext': ext,
                            'filesize': filesize,
                            'vcodec': vcodec,
                            'acodec': acodec
                        }
            
            logger.info(f"Найдено {len(formats)} комбинированных форматов")
            
            # Если не найдены комбинированные - пробуем найти лучший выбор
            if not formats:
                logger.warning("Нет комбинированных форматов, ищем альтернативы...")
                
                # Получаем лучший формат автоматически
                try:
                    with yt_dlp.YoutubeDL({'format': 'best', 'quiet': True}) as ydl_best:
                        info_best = ydl_best.extract_info(url, download=False)
                        best_fmt = info_best.get('format_id', 'best')
                        formats['best'] = {
                            'format_id': best_fmt,
                            'quality': 'Лучший доступный',
                            'ext': info_best.get('ext', 'mp4'),
                            'filesize': info_best.get('filesize', 0)
                        }
                except Exception as e:
                    logger.error(f"Ошибка при получении лучшего формата: {e}")
            
            result_formats = sorted(
                list(formats.values()),
                key=lambda x: int(x['quality'].replace('p', '')) if x['quality'] != 'Лучший доступный' and x['quality'] != 'Unknown' else 0,
                reverse=True
            )
            
            return jsonify({
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'formats': result_formats
            })
    
    except Exception as e:
        logger.error(f"Ошибка при получении форматов: {str(e)}", exc_info=True)
        return jsonify({'error': f'Ошибка: {str(e)}'}), 400

@app.route('/api/download', methods=['POST'])
def download():
    """Скачать видео"""
    try:
        data = request.json
        url = data.get('url')
        format_id = data.get('format_id')
        
        logger.info(f"Попытка скачивания: URL={url}, format_id={format_id}")
        
        if not url or not format_id:
            return jsonify({'error': 'Неполные данные'}), 400
        
        ydl_opts = get_ydl_opts(format_id, download=True)
        
        logger.info(f"Начинаем скачивание видео с форматом {format_id}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            logger.info(f"Видео успешно скачано: {filename}")
            
            return jsonify({
                'success': True,
                'message': f'Видео успешно скачано: {info.get("title")}'
            })
    
    except Exception as e:
        logger.error(f"Ошибка при скачивании: {str(e)}", exc_info=True)
        return jsonify({'error': f'Ошибка при скачивании: {str(e)}'}), 400

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """Получить список скачанных видео"""
    try:
        files = []
        if DOWNLOADS_FOLDER.exists():
            for file in DOWNLOADS_FOLDER.iterdir():
                if file.is_file():
                    files.append({
                        'name': file.name,
                        'size': file.stat().st_size,
                        'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                    })
        
        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify(files)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
