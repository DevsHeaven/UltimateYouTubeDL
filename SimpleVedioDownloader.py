import os
from flask import Flask, render_template_string, request, send_file, abort
import yt_dlp
import urllib.parse

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Simple YouTube Downloader</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f9f9f9; padding: 20px; border-radius: 8px; }
        input, button, select { padding: 8px; margin: 5px 0; font-size: 16px; }
        button { background: #ff0000; color: white; border: none; cursor: pointer; }
        .status { margin-top: 15px; font-weight: bold; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="color: #ff0000;">Simple YouTube Downloader</h2>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube URL here" style="width: 80%;" required>
            <br><br>
            <label>Download as:</label>
            <select name="format">
                <option value="video">Video (MP4)</option>
                <option value="audio">Audio Only (M4A)</option>
            </select>
            <button type="submit">Download</button>
        </form>

        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}

        {% if filename %}
            <p class="success">
                ✅ Download complete! <a href="/download/{{ filename }}">Click to save "{{ filename }}"</a>
            </p>
        {% endif %}
    </div>
</body>
</html>
'''

def get_format(download_format):
    """Returns format selector that doesn't require FFmpeg"""
    return {
        'video': 'best[ext=mp4]',  # Single file MP4 format
        'audio': 'bestaudio[ext=m4a]'  # Audio in M4A container
    }.get(download_format, 'best[ext=mp4]')

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    filename = None
    
    if request.method == 'POST':
        url = request.form['url']
        download_format = request.form.get('format', 'video')
        
        # Create downloads directory if it doesn't exist
        download_dir = os.path.abspath('downloads')
        os.makedirs(download_dir, exist_ok=True)

        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'format': get_format(download_format),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = os.path.basename(ydl.prepare_filename(info))
                
        except Exception as e:
            error = f"Download failed: {str(e)}"

    return render_template_string(HTML, error=error, filename=filename)

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