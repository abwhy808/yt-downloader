#!/usr/bin/env python3
"""
Диагностический скрипт для проверки проблем со скачиванием видео
"""

import yt_dlp
import sys
from pathlib import Path

def test_yt_dlp():
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ yt-dlp")
    print("=" * 60)
    
    # Используйте реальный URL, если хотите протестировать
    test_url = input("Введите URL видео YouTube (или оставьте пусто для пропуска): ").strip()
    
    if not test_url:
        print("Пропуск теста URL")
        return
    
    try:
        print(f"\n1. Проверка доступа к YouTube для: {test_url}")
        
        ydl_opts = {
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'extractor_args': {'youtube': {'player_client': ['web']}},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("\n2. Загрузка информации о видео...")
            info = ydl.extract_info(test_url, download=False)
            
            print(f"\n✓ Успешно! Видео: {info.get('title')}")
            print(f"  Длительность: {info.get('duration')} сек")
            print(f"  Загружено форматов: {len(info.get('formats', []))}")
            
            print("\n3. Доступные форматы:")
            combined_formats = []
            for fmt in info.get('formats', []):
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    combined_formats.append(fmt)
                    height = fmt.get('height', '?')
                    ext = fmt.get('ext', '?')
                    fid = fmt.get('format_id')
                    filesize = fmt.get('filesize', 0)
                    size_mb = filesize / (1024*1024) if filesize else 0
                    print(f"   - {height}p {ext}: ID={fid}, Size={size_mb:.1f}MB")
            
            if not combined_formats:
                print("   ⚠ Не найдены форматы с видео И аудио")
            
            if combined_formats:
                print("\n4. Пробуем скачать первый формат...")
                fmt_id = combined_formats[0]['format_id']
                
                ydl_opts_download = {
                    'format': fmt_id,
                    'outtmpl': 'test_video_%(title)s.%(ext)s',
                    'quiet': False,
                    'no_warnings': False,
                    'socket_timeout': 30,
                    'retries': 10,
                    'fragment_retries': 10,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl2:
                    print(f"   Скачивание в формате {fmt_id}...")
                    info2 = ydl2.extract_info(test_url, download=True)
                    print(f"   ✓ Успешно скачано!")
    
    except Exception as e:
        print(f"\n✗ ОШИБКА: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_yt_dlp()
    sys.exit(0 if success else 1)
