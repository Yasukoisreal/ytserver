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
    return "🚀 API Railway (Fix Lỗi Trống Tab Home) đang hoạt động!"

# =======================================================
# LẤY BẢNG XẾP HẠNG (ĐÃ FIX LỖI RỖNG)
# =======================================================
@app.route('/api/trending')
def trending_music():
    client_key = request.args.get("key")
    if client_key != SECRET_KEY:
        return jsonify({"error": "Unauthorized!"}), 403

    region = request.args.get('region', 'VN') 
    
    try:
        charts = ytmusic.get_charts(country=region)
        chart_items = []
        
        # Quét tất cả các danh mục có thể chứa nhạc
        for key in ['videos', 'songs', 'trending']:
            if key in charts and 'items' in charts[key]:
                chart_items.extend(charts[key]['items'])
        
        # KẾ HOẠCH DỰ PHÒNG: Nếu API YouTube lỗi không trả về Chart, tự động Search Top bài hát
        if not chart_items:
            chart_items = ytmusic.search(f"top songs {region}", filter="songs", limit=15)
            
        items = []
        for item in chart_items:
            try:
                video_id = item['videoId']
                title = item['title']
                artists = ", ".join([artist['name'] for artist in item.get('artists', [])]) if 'artists' in item else "Unknown Artist"
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
            except Exception:
                continue
                
        # Trả về đúng 15 bài đầu tiên để App Lumia chạy mượt
        return jsonify({"items": items[:15]})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# =======================================================
# TÌM KIẾM BÀI HÁT
# =======================================================
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
            except Exception:
                continue
        return jsonify({"items": items})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# =======================================================
# BƠM NHẠC TRỰC TIẾP (Proxy)
# =======================================================
@app.route('/api/play')
def play_audio():
    client_key = request.args.get("key")
    if client_key != SECRET_KEY:
        return jsonify({"error": "Unauthorized!"}), 403

    video_id = request.args.get('v')
    if not video_id:
        return "Lỗi: Thiếu ID", 400

    audio_url = url_cache.get(video_id)

    if not audio_url:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'format': '140/bestaudio[ext=m4a]/18/best[ext=mp4]',
            'extractor_args': {'youtube': {'client': ['ios', 'tv', 'web']}}, 
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

    try:
        req_headers = {}
        if "Range" in request.headers:
            req_headers["Range"] = request.headers["Range"]
            
        r = requests.get(audio_url, headers=req_headers, stream=True)
        
        if r.status_code in [403, 401]:
            if video_id in url_cache:
                del url_cache[video_id]
            return "🚨 Bị khóa IP. Đã xóa cache, vui lòng chọn lại bài hát!", 403

        def generate():
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk

        excluded_headers = ['content-encoding', 'transfer-encoding', 'connection']
        resp_headers = []
        for k, v in r.headers.items():
            if k.lower() not in excluded_headers:
                resp_headers.append((k, v))
                
        return Response(generate(), status=r.status_code, headers=resp_headers, direct_passthrough=True)

    except Exception as e:
        traceback.print_exc()
        return f"🚨 Lỗi Stream: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
