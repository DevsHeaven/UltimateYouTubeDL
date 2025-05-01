import os
import subprocess
from flask import Flask, render_template_string, request, send_file, abort
import yt_dlp
import urllib.parse

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Ultimate YouTube Downloader</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f9f9f9; padding: 20px; border-radius: 8px; }
        select, input, button { padding: 8px; margin: 5px 0; font-size: 16px; }
        button { background: #ff0000; color: white; border: none; cursor: pointer; }
        .quality-info { margin: 10px 0; font-size: 14px; color: #666; }
        .max-quality { color: #ff0000; font-weight: bold; }
        .warning { color: #ff9900; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="color: #ff0000;">Ultimate YouTube Downloader</h2>
        
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube URL here" style="width: 80%;" required>
            <br><br>
            <label>Select Quality:</label>
            <select name="quality" id="quality-select" onchange="showQualityInfo()">
                <option value="max">Maximum Possible (4K/8K)</option>
                <option value="1080">Full HD (1080p)</option>
                <option value="720">HD (720p)</option>
                <option value="audio">Audio Only (320kbps)</option>
            </select>
            
            <div id="quality-info" class="quality-info">
                <span class="max-quality">✔ Will download the absolute best quality available</span>
                {% if not ffmpeg_available %}
                <span class="warning"><br>⚠ FFmpeg not found - maximum quality may be limited</span>
                {% endif %}
            </div>
            
            <button type="submit">DOWNLOAD NOW</button>
        </form>

        {% if error %}
            <p style="color: red;">{{ error }}</p>
        {% endif %}

        {% if filename %}
            <p style="color: green; font-weight: bold;">
                ✅ Download complete! <a href="/download/{{ filename }}">Click to save "{{ filename }}"</a>
            </p>
        {% endif %}
    </div>

    <script>
        function showQualityInfo() {
            const quality = document.getElementById('quality-select').value;
            const infoDiv = document.getElementById('quality-info');
            
            if (quality === 'max') {
                infoDiv.innerHTML = `<span class="max-quality">✔ Will download 4K/8K if available</span>`;
            } else if (quality === '1080') {
                infoDiv.innerHTML = `✔ 1080p Full HD quality`;
            } else if (quality === 'audio') {
                infoDiv.innerHTML = `✔ High quality audio (320kbps MP3)`;
            }
            {% if not ffmpeg_available %}
            infoDiv.innerHTML += `<span class="warning"><br>⚠ FFmpeg not found - maximum quality may be limited</span>`;
            {% endif %}
        }
    </script>
</body>
</html>
'''

def get_ffmpeg_path():
    """Find FFmpeg executable path with cross-platform support"""
    try:
        # Try different methods to find ffmpeg
        if os.name == 'nt':  # Windows
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, shell=True)
        else:  # Linux/Mac
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout.split('\n')[0].strip()
        
        # Check common installation paths
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            'C:\\FFmpeg\\bin\\ffmpeg.exe',
            'C:\\Program Files\\FFmpeg\\bin\\ffmpeg.exe'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        return None
    except Exception as e:
        print(f"Error finding FFmpeg: {e}")
        return None

def get_best_format(quality, ffmpeg_available):
    """Return appropriate format selector based on FFmpeg availability"""
    format_options = {
        'max': {
            True: 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            False: 'best[ext=mp4]'
        },
        '1080': {
            True: 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            False: 'best[height<=1080][ext=mp4]'
        },
        '720': {
            True: 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
            False: 'best[height<=720][ext=mp4]'
        },
        'audio': {
            True: 'bestaudio/best',
            False: 'bestaudio[ext=m4a]/bestaudio'
        }
    }
    return format_options[quality][ffmpeg_available]

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    filename = None
    ffmpeg_path = get_ffmpeg_path()
    ffmpeg_available = ffmpeg_path is not None
    
    if request.method == 'POST':
        url = request.form['url']
        quality = request.form.get('quality', 'max')
        
        download_dir = os.path.abspath('downloads')
        os.makedirs(download_dir, exist_ok=True)

        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'format': get_best_format(quality, ffmpeg_available),
            'noplaylist': True,
            'restrictfilenames': True,
            'nooverwrites': True,
            'verbose': True
        }

        if ffmpeg_available:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            ydl_opts['merge_output_format'] = 'mp4'
            
            if quality != 'audio':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
            else:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]
        else:
            ydl_opts['merge_output_format'] = None

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = os.path.basename(ydl.prepare_filename(info))
                
                if quality == 'audio':
                    if ffmpeg_available:
                        filename = filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')
                    else:
                        filename = filename.replace('.webm', '.m4a')
                
        except Exception as e:
            error = f"Download failed: {str(e)}"
            if "FFmpeg" in str(e):
                error += " - FFmpeg was found but not working properly"

    return render_template_string(
        HTML, 
        error=error, 
        filename=filename,
        ffmpeg_available=ffmpeg_available
    )

@app.route('/download/<filename>')
def download(filename):
    try:
        download_dir = os.path.abspath('downloads')
        safe_filename = urllib.parse.unquote(filename)
        path = os.path.join(download_dir, safe_filename)
        
        if not os.path.exists(path):
            abort(404, description="File not found")
            
        return send_file(path, as_attachment=True)
    except Exception as e:
        abort(500, description=str(e))

if __name__ == '__main__':
    os.makedirs('downloads', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)