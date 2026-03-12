import os
import traceback
import requests
from flask import Flask, request, jsonify, Response
from cachetools import TTLCache
import yt_dlp
from ytmusicapi import YTMusic

app = Flask(__name__)

# Cache lưu trữ link 30 phút
url_cache = TTLCache(maxsize=1000, ttl=1800)
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "LumiaWP81-An")
ytmusic = YTMusic()

@app.route('/')
def home():
    return "🚀 API Railway (Proxy Streaming) đang hoạt động mượt mà!"

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
        return jsonify({"error": "Unauthorized!"}), 403

    video_id = request.args.get('v')
    if not video_id:
        return "Lỗi: Thiếu ID", 400

    audio_url = url_cache.get(video_id)

    # Nếu chưa có link trong RAM thì gọi yt-dlp để đào link
    if not audio_url:
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
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=False)
                audio_url = info_dict.get('url')
                if not audio_url:
                    return "Không tìm thấy định dạng âm thanh.", 500
                url_cache[video_id] = audio_url
        except Exception as e:
            traceback.print_exc()
            return f"🚨 Lỗi yt-dlp: {str(e)}", 500

    # =======================================================
    # BÍ KÍP TỐI THƯỢNG: SERVER PROXY STREAMING
    # Ép server Railway tự làm "ống hút" tải nhạc rồi bơm về Lumia 530
    # =======================================================
    try:
        req_headers = {}
        # Hứng header "Range" từ điện thoại để giữ được chức năng tua nhạc (Seek)
        if "Range" in request.headers:
            req_headers["Range"] = request.headers["Range"]
            
        r = requests.get(audio_url, headers=req_headers, stream=True)
        
        # Nếu Google từ chối, xóa link chết khỏi RAM để lần sau đào link mới
        if r.status_code in [403, 401]:
            if video_id in url_cache:
                del url_cache[video_id]
            return "🚨 Bị khóa IP. Đã xóa cache, bấm chọn lại bài hát nhé!", 403

        # Đóng gói dòng chảy (chunk) để tiết kiệm RAM cho Server Railway
        def generate():
            for chunk in r.iter_content(chunk_size=16384):
                if chunk:
                    yield chunk

        resp = Response(generate(), status=r.status_code)
        
        # Bê y nguyên các thông số âm lượng, độ dài bài hát từ Google sang Lumia 530
        for key in ["Content-Type", "Accept-Ranges", "Content-Length", "Content-Range"]:
            if key in r.headers:
                resp.headers[key] = r.headers[key]
                
        return resp

    except Exception as e:
        traceback.print_exc()
        return f"🚨 Lỗi Stream: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
