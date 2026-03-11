import os
import time
import traceback
from flask import Flask, request, redirect, jsonify
from cachetools import TTLCache
import yt_dlp
from ytmusicapi import YTMusic

app = Flask(__name__)

# Giảm thời gian Cache xuống 30 phút để tránh dính link hết hạn (Expired Token)
url_cache = TTLCache(maxsize=1000, ttl=1800)

SECRET_KEY = os.environ.get("APP_SECRET_KEY", "LumiaWP81-An")
ytmusic = YTMusic()

cookie_data = os.environ.get('COOKIE_DATA')
if cookie_data:
    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write(cookie_data)

@app.route('/')
def home():
    return "🚀 API Railway (Fix Lỗi 403 & SSL) đang hoạt động!"

@app.route('/api/search')
def search_music():
    client_key = request.args.get("key")
    if client_key != SECRET_KEY:
        return jsonify({"error": "Unauthorized!"}), 403

    query = request.args.get('q')
    if not query:
        return jsonify({"error": "Missing query"}), 400

    try:
        search_results = ytmusic.search(query, filter="songs", limit=15)
        
        items = []
        for item in search_results:
            try:
                video_id = item['videoId']
                title = item['title']
                artists = ", ".join([artist['name'] for artist in item.get('artists', [])])
                
                thumbnails = item.get('thumbnails', [])
                thumb_url = thumbnails[-1]['url'] if thumbnails else ""
                
                items.append({
                    "id": {"videoId": video_id},
                    "snippet": {
                        "title": title,
                        "channelTitle": artists,
                        "thumbnails": {
                            "default": {"url": thumb_url},
                            "medium": {"url": thumb_url},
                            "high": {"url": thumb_url}
                        }
                    }
                })
            except Exception as e:
                continue
                
        return jsonify({"items": items})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/play')
def play_audio():
    client_key = request.args.get("key")
    if client_key != SECRET_KEY:
        return jsonify({"error": "Unauthorized! Đi chỗ khác chơi!"}), 403

    video_id = request.args.get('v')
    if not video_id:
        return "Lỗi: Thiếu ID bài hát", 400

    if video_id in url_cache:
        print(f"⚡ [CACHE HIT] Lấy link bài {video_id} cực nhanh từ RAM!")
        return redirect(url_cache[video_id])

    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': '140/bestaudio[ext=m4a]/18/best[ext=mp4]',
        # BÍ KÍP 1: Ép yt-dlp dùng client iOS để lách luật khóa IP (IP Binding) của Google
        'extractor_args': {'youtube': {'client': ['ios', 'tv', 'web']}}, 
        'youtube_include_dash_manifest': False,
        'youtube_include_hls_manifest': False,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True
    }
    
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            audio_url = info_dict.get('url')

            if not audio_url:
                return "Không tìm thấy định dạng âm thanh.", 500

            # BÍ KÍP 2: Đánh lừa chứng chỉ bảo mật (SSL/TLS) của Windows Phone 8.1
            # Hạ cấp xuống HTTP thuần sẽ giúp trình phát nhạc kết nối mượt mà ngay lập tức!
            audio_url = audio_url.replace("https://", "http://")

            url_cache[video_id] = audio_url
            return redirect(audio_url)

    except Exception as e:
        traceback.print_exc()
        return f"🚨 Lỗi: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
