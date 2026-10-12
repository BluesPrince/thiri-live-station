#!/usr/bin/env python3
"""
THIRI // Conductor Console Web Server
Lightweight, zero-dependency HTTP server providing the web UI and REST API
to steer the 24/7 autonomous live station in real time.
"""

import os, sys, json, time, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, 'stream_state.json')
CATALOG_FILE = os.path.join(HERE, 'audio', 'lofi_beats', 'lofi_20_beats_catalog.json')
WEB_DIR = os.path.join(HERE, 'web')
AUDIO_DIR = os.path.join(HERE, 'audio', 'lofi_beats')

PORT = int(os.environ.get('PORT', 8900))

class ConductorHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        resp = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(resp)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(resp)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if path in ('/', '/index.html', '/conductor'):
            index_path = os.path.join(WEB_DIR, 'conductor.html')
            if not os.path.exists(index_path):
                self.send_error(404, "conductor.html not found")
                return
            with open(index_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        elif path == '/api/state':
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
            except Exception:
                state = {}
            self._send_json(state)
            return

        elif path == '/api/beats':
            try:
                with open(CATALOG_FILE, 'r') as f:
                    beats = json.load(f)
            except Exception:
                beats = []
            self._send_json(beats)
            return

        elif path.startswith('/audio/'):
            filename = os.path.basename(path)
            file_path = os.path.join(AUDIO_DIR, filename)
            if os.path.exists(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                with open(file_path, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', mime or 'audio/mpeg')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                self.send_error(404, "Audio file not found")
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path

        if path == '/api/control':
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len).decode('utf-8')
            try:
                updates = json.loads(body)
            except Exception as e:
                self._send_json({'error': f'Invalid JSON: {e}'}, status=400)
                return

            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
            except Exception:
                state = {}

            # Apply updates
            state.update(updates)
            state["updated_at"] = time.time()

            # If active_beat updated, find matching beat name
            if "active_beat" in updates:
                try:
                    with open(CATALOG_FILE, 'r') as f:
                        cat = json.load(f)
                    b_id = int(updates["active_beat"])
                    for item in cat:
                        if item.get("id") == b_id:
                            state["beat_name"] = item.get("name")
                            state["beat_style"] = item.get("style")
                            state["tempo_bpm"] = float(item.get("bpm", state.get("tempo_bpm", 90.0)))
                            state["active_key"] = item.get("key", state.get("active_key", "C")).split()[0]
                            break
                except Exception:
                    pass

            # Write updated state
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)

            self._send_json({"success": True, "state": state})
            return

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # Keep logs clean
        return

def main():
    os.makedirs(WEB_DIR, exist_ok=True)
    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, ConductorHandler)
    print("=================================================================")
    print(f"   THIRI // Conductor Console Web Server running on port {PORT}")
    print(f"   Local Console URL: http://localhost:{PORT}/")
    print("=================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nConductor server stopped.")
        httpd.server_close()

if __name__ == '__main__':
    main()
