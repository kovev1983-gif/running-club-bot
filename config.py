import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BACKUP_TIME = '00:00'  # 3:00 MSK (полночь UTC)
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []
DATABASE_NAME = 'running_club.db'
BACKUP_NAME = 'backup_running_club.db'


