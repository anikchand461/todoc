from pathlib import Path

APP_NAME = "todoc"
DATA_FILE_NAME = ".todoc_tasks.json"

# Default path: User Home Directory
DATA_FILE_PATH = Path.home() / DATA_FILE_NAME
