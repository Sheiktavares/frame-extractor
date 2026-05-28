from flask import Flask, request, jsonify
import subprocess, tempfile, os, requests, base64

app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    ts_url = data.get('url')
    if not ts_url:
        return jsonify({'error': 'no url'}), 400

    # Baixa o segmento .ts
    r = requests.get(ts_url, timeout=15, verify=False)
    if r.status_code != 200:
        return jsonify({'error': 'download failed'}), 500

    with tempfile.TemporaryDirectory() as tmp:
        ts_file  = os.path.join(tmp, 'seg.ts')
        jpg_file = os.path.join(tmp, 'frame.jpg')

        open(ts_file, 'wb').write(r.content)

        # Extrai frame com FFmpeg
        cmd = ['ffmpeg', '-i', ts_file, '-vf', 'select=eq(n\\,5)',
               '-vframes', '1', '-q:v', '2', jpg_file, '-y']
        result = subprocess.run(cmd, capture_output=True, timeout=20)

        if not os.path.exists(jpg_file):
            return jsonify({'error': 'ffmpeg failed', 'stderr': result.stderr.decode()}), 500

        # Retorna frame em base64
        with open(jpg_file, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode()

        return jsonify({'frame': img_b64})

@app.route('/')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
