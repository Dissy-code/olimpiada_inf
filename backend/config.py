import os

PORT = 8082
DB_FILE = "olympiad_platform.db"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "frontend")
INDEX_PATH = os.path.join(FRONTEND_DIR, "index.html")
