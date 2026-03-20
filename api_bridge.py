import http.server
import socketserver
import json
import subprocess
import threading
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("API-Bridge")

PORT = 8000
STATUS_FILE = "enricher_status.json"

class PipelineManager:
    """Manages the lifecycle of background pipeline processes."""
    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.start_time: datetime | None = None
        self.last_run_status = "idle"

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def start(self, script_name="main.py"):
        if self.is_running():
            return False, "Pipeline already running"
        
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd()
            logger.info(f"🚀 Starting pipeline: {script_name}")
            
            # Use subprocess.Popen to run in background
            creation_flags = 0
            if os.name == 'nt':
                # CREATE_NEW_PROCESS_GROUP = 0x00000200
                creation_flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)

            self.process = subprocess.Popen(
                [sys.executable, script_name],
                env=env,
                creationflags=creation_flags
            )
            self.start_time = datetime.now()
            self.last_run_status = "running"
            return True, "Pipeline started successfully"
        except Exception as e:
            logger.error(f"❌ Failed to start pipeline: {e}")
            return False, str(e)

    def stop(self):
        if not self.is_running() or not self.process:
            return False, "No pipeline running"
        
        try:
            logger.info(f"🛑 Stopping pipeline PID {self.process.pid}...")
            if os.name == 'nt' and self.process:
                # On Windows, use taskkill to ensure child processes are also killed
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], capture_output=True)
            elif self.process:
                self.process.terminate()
                
            if self.process:
                self.process.wait(timeout=5)
            self.process = None
            self.last_run_status = "stopped"
            return True, "Pipeline stopped"
        except Exception as e:
            logger.error(f"❌ Error stopping pipeline: {e}")
            return False, str(e)

    def get_status(self):
        runtime = None
        if self.start_time and self.is_running():
            runtime = str(datetime.now() - self.start_time).split('.')[0]
            
        return {
            "running": self.is_running(),
            "status": self.last_run_status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "runtime": runtime,
            "pid": self.process.pid if self.is_running() else None
        }

# Global manager instance
manager = PipelineManager()

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
            self.get_full_status()
        elif self.path == '/enrichment/stats':
            self.get_enrichment_stats()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        if self.path == '/pipeline/run':
            success, msg = manager.start("main.py")
            self._set_headers(200 if success else 400)
            self.wfile.write(json.dumps({"success": success, "message": msg}).encode())
        elif self.path == '/pipeline/stop':
            success, msg = manager.stop()
            self._set_headers(200 if success else 400)
            self.wfile.write(json.dumps({"success": success, "message": msg}).encode())
        elif self.path == '/audit/refresh':
            success, msg = manager.start("refresh_audit.py")
            self._set_headers(200 if success else 400)
            self.wfile.write(json.dumps({"success": success, "message": msg}).encode())
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def get_full_status(self):
        """Combines process status with file status."""
        try:
            status = manager.get_status()
            
            # Load stats from file if exists
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r') as f:
                    file_data = json.load(f)
                    status["progress"] = file_data
            
            self._set_headers()
            self.wfile.write(json.dumps(status).encode())
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def get_enrichment_stats(self):
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

def run():
    logger.info(f"🛰️  BPP API Bridge active on port {PORT}")
    logger.info("📡 Available Endpoints:")
    logger.info(f"  GET  /status           - Get full pipeline & progress status")
    logger.info(f"  GET  /enrichment/stats - Get quick metrics")
    logger.info(f"  POST /pipeline/run    - Start full main pipeline")
    logger.info(f"  POST /pipeline/stop   - Stop current pipeline")
    logger.info(f"  POST /audit/refresh    - Trigger manual audit recalculation")
    
    try:
        with socketserver.TCPServer(("", PORT), PipelineHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Gracefully shutting down...")
    except Exception as e:
        logger.error(f"Bridge crash: {e}")

if __name__ == "__main__":
    run()
