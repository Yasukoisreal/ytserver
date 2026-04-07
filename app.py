import os
import traceback
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "LumiaWP81-An")

@app.route('/')
def home():
    return "🚀 API Railway (Bản Trả Chuỗi Text Siêu Tốc) đang hoạt động!"

# ==================================================
# CỔNG NGHE NHẠC: TRẢ VỀ DÒNG TEXT (LINK TRỰC TIẾP TỪ GOOGLE)
# ==================================================
@app.route('/api/play')
def play_audio():
    client_key = request.args.get("key")
    if client_key != SECRET_KEY:
        return "Unauthorized", 403

    video_id = request.args.get('v')
    if not video_id: return "Lỗi ID bài hát", 400

    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Chỉ bóc tách lấy link (download=False)
    ydl_opts = {
        'format': '140', # Định dạng chuẩn M4A tương thích 100% WP8.1
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'client': ['android', 'ios', 'tv', 'web']}}
    }
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            direct_url = info['url']
            
            # Chỉ trả về một chuỗi văn bản là đường link
            return direct_url
    except Exception as e:
        return f"Error: {str(e)}", 500

# ==================================================
# CỔNG TẢI OFFLINE (Giữ nguyên như cũ cho chức năng Download)
# ==================================================
DOWNLOAD_DIR = "/tmp/ytmusic"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@app.route('/api/download')
def download_audio():
    client_key = request.args.get("key")
    if client_key != SECRET_KEY:
        return "Unauthorized", 403

    video_id = request.args.get('v')
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.m4a")
    
    if not os.path.exists(file_path):
        ydl_opts = {
            'format': '140',
            'outtmpl': file_path,
            'noplaylist': True,
            'quiet': True
        }
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        except Exception as e:
            return f"Error: {str(e)}", 500
            
    return send_file(file_path, mimetype="audio/mp4", as_attachment=True, download_name=f"{video_id}.m4a")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
