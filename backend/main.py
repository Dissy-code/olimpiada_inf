import socketserver
import threading
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PORT, DB_FILE, FRONTEND_DIR, INDEX_PATH
from database import init_database
from api_handlers import OlympiadHandler
from websocket_server import WebSocketServer

def start_servers():
    init_database()
    
    ws_server = WebSocketServer()
    ws_thread = threading.Thread(target=ws_server.start, daemon=True)
    ws_thread.start()
    
    httpd_server = socketserver.TCPServer(
        ("", PORT), 
        lambda *args, **kwargs: OlympiadHandler(*args, ws_server_instance=ws_server, **kwargs)
    )
    
    with httpd_server as httpd:
        print(f"🚀 HTTP server running on http://localhost:{PORT}")
        print(f"🌐 Open browser: http://localhost:{PORT}")
        print(f"👑 Admin: admin / admin123")
        print(f"👤 Test user: test / test123")
        print(f"📊 Database: {DB_FILE}")
        print(f"📁 Frontend directory: {FRONTEND_DIR}")
        if not os.path.exists(INDEX_PATH):
            print(f"⚠️ File {INDEX_PATH} not found!")
        print("⚡ Press Ctrl+C to stop server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")
            httpd.server_close()

if __name__ == "__main__":
    start_servers()
