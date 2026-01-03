from apscheduler.schedulers.background import BackgroundScheduler
from database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def schedule_backup():
    """Планировщик резервного копирования"""
    scheduler = BackgroundScheduler()
    db = Database()
    
    def perform_backup():
        try:
            db.backup_database()
            logger.info("Scheduled backup completed successfully")
        except Exception as e:
            logger.error(f"Backup error: {e}")
    
    # Ежедневное резервное копирование в 3:00 MSK (00:00 UTC)
    scheduler.add_job(perform_backup, 'cron', hour=0, minute=0)
    
    scheduler.start()
    return scheduler
