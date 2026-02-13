import http.server
import socketserver
import json
import subprocess
import threading
import os
from datetime import datetime

PORT = 8000
STATUS_FILE = "enricher_status.json"
PROCESS = None

class PipelineHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        if self.path == '/status':
            self.get_status()
        elif self.path == '/enrichment/stats':
            self.get_enrichment_stats()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        if self.path == '/pipeline/run':
            self.run_pipeline()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def get_status(self):
        """Returns the content of enricher_status.json"""
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r') as f:
                    data = json.load(f)
            else:
                data = {"running": False, "message": "No status file found"}
            
            # Enrich with process check
            global PROCESS
            if PROCESS and PROCESS.poll() is None:
                data["pipeline_running"] = True
            else:
                data["pipeline_running"] = False

            self._set_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def get_enrichment_stats(self):
        """Returns a quick summary of enriched vs pending from local status."""
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r') as f:
                    data = json.load(f)
                stats = {
                    "total": data.get("total_products", 0),
                    "processed": data.get("processed", 0),
                    "enriched": data.get("enriched", 0),
                    "failed": data.get("failed", 0),
                    "pending": data.get("total_products", 0) - data.get("processed", 0)
                }
            else:
                stats = {"message": "Status file initializing..."}
                
            self._set_headers()
            self.wfile.write(json.dumps(stats).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def run_pipeline(self):
        """Starts the pipeline in a separate process."""
        global PROCESS
        if PROCESS and PROCESS.poll() is None:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Pipeline is already running"}).encode())
            return

        def start_script():
            global PROCESS
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd()
            # Run main.py which now includes Scrape -> Enrich -> Audit
            PROCESS = subprocess.Popen(["python", "main.py"], env=env)
            PROCESS.wait()

        thread = threading.Thread(target=start_script)
        thread.start()

        self._set_headers()
        self.wfile.write(json.dumps({"status": "started", "timestamp": datetime.now().isoformat()}).encode())

def run():
    print(f"BPP API Bridge started on port {PORT}")
    print("Endpoints:")
    print(f"  GET  http://localhost:{PORT}/status")
    print(f"  GET  http://localhost:{PORT}/enrichment/stats")
    print(f"  POST http://localhost:{PORT}/pipeline/run")
    
    with socketserver.TCPServer(("", PORT), PipelineHandler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    run()
