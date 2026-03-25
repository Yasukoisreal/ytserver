import os
import time
import traceback
from flask import Flask, request, redirect, jsonify
from cachetools import TTLCache
import yt_dlp

app = Flask(__name__)

# TỐI ƯU 1: CACHE CHỐNG TRÀN RAM (RAM 512MB CỦA RAILWAY LUÔN AN TOÀN)
url_cache = TTLCache(maxsize=1000, ttl=7200)

# TỐI ƯU 2: KHÓA BẢO MẬT CHỐNG XÀI CHÙA
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "LumiaWP81-An")

# TỐI ƯU 3: NẠP COOKIE CHỐNG GIỚI HẠN ĐỘ TUỔI
cookie_data = os.environ.get('COOKIE_DATA')
if cookie_data:
    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write(cookie_data)

@app.route('/')
def home():
    return "🚀 API Railway (Bản Tối Thượng) đang hoạt động!"

@app.route('/api/play')
def play_audio():
    # Kiểm tra khóa bảo mật truyền qua URL (?key=...)
    client_key = request.args.get("key")
    if client_key != SECRET_KEY:
        return jsonify({"error": "Unauthorized! Đi chỗ khác chơi!"}), 403

    video_id = request.args.get('v')
    if not video_id:
        return "Lỗi: Thiếu ID bài hát", 400

    # Lấy link từ RAM siêu tốc nếu có
    if video_id in url_cache:
        print(f"⚡ [CACHE HIT] Lấy link bài {video_id} cực nhanh từ RAM!")
        return redirect(url_cache[video_id])

    # YT-DLP GIẢ LẬP ĐIỆN THOẠI ĐỂ VƯỢT RÀO
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': '140/bestaudio[ext=m4a]/18/best[ext=mp4]',
        'extractor_args': {'youtube': {'client': ['android', 'ios', 'tv', 'web']}},
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

            url_cache[video_id] = audio_url
            return redirect(audio_url)

    except Exception as e:
        traceback.print_exc()
        return f"🚨 Lỗi: {str(e)}", 500

if __name__ == '__main__':
    # Bắt Port động của Railway
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
