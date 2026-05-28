from flask import Flask, request, jsonify
import subprocess, tempfile, os, requests, base64, glob, json

app = Flask(__name__)

# Zona de contagem — entre as duas vias da SP-008 KM94.5
# Coordenadas normalizadas (0 a 1) baseadas na análise do frame
ZONE_X1 = 0.03   # início esquerdo da pista
ZONE_X2 = 0.82   # fim direito da pista
ZONE_Y1 = 0.45   # topo da zona de contagem
ZONE_Y2 = 0.75   # base da zona de contagem

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    ts_url = data.get('url')
    if not ts_url:
        return jsonify({'error': 'no url'}), 400

    try:
        r = requests.get(ts_url, timeout=15, verify=False)
        if r.status_code != 200:
            return jsonify({'error': 'download failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    with tempfile.TemporaryDirectory() as tmp:
        ts_file = os.path.join(tmp, 'seg.ts')
        with open(ts_file, 'wb') as f:
            f.write(r.content)

        # Extrai 1 frame a cada 2 segundos (~5 frames por segmento de 9.6s)
        pattern = os.path.join(tmp, 'frame_%03d.jpg')
        cmd = ['ffmpeg', '-i', ts_file,
               '-vf', 'fps=0.5',
               '-q:v', '2',
               pattern, '-y']
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        frames = sorted(glob.glob(os.path.join(tmp, 'frame_*.jpg')))
        if not frames:
            return jsonify({'error': 'no frames', 'stderr': result.stderr.decode()[:500]}), 500

        # Retorna frames em base64 + frame principal para exibição
        frames_b64 = []
        for f in frames:
            with open(f, 'rb') as fp:
                frames_b64.append(base64.b64encode(fp.read()).decode())

        # Frame do meio para exibição visual
        mid = frames_b64[len(frames_b64)//2]

        return jsonify({
            'frames': frames_b64,
            'display_frame': mid,
            'count': len(frames_b64),
            'zone': {
                'x1': ZONE_X1, 'y1': ZONE_Y1,
                'x2': ZONE_X2, 'y2': ZONE_Y2
            }
        })

@app.route('/')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
