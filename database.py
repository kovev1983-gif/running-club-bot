import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='running_club.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица никнеймов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nicknames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_username TEXT NOT NULL,
                nickname TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица тренировок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                distance REAL NOT NULL,
                duration INTEGER NOT NULL,
                telegram_username TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_nickname(self, telegram_username, nickname):
        """Добавление или обновление никнейма"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже запись
        cursor.execute('SELECT id FROM nicknames WHERE telegram_username = ?', (telegram_username,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE nicknames 
                SET nickname = ?, registration_date = CURRENT_TIMESTAMP 
                WHERE telegram_username = ?
            ''', (nickname, telegram_username))
        else:
            cursor.execute('''
                INSERT INTO nicknames (telegram_username, nickname) 
                VALUES (?, ?)
            ''', (telegram_username, nickname))
        
        conn.commit()
        conn.close()
    
    def get_nickname(self, telegram_username):
        """Получение никнейма пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT nickname FROM nicknames 
            WHERE telegram_username = ?
        ''', (telegram_username,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def add_workout(self, telegram_username, distance, duration):
        """Добавление тренировки"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO workouts (telegram_username, distance, duration)
            VALUES (?, ?, ?)
        ''', (telegram_username, distance, duration))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self, period='all', username=None):
        """Получение статистики"""
        conn = self.get_connection()
        
        # Определяем период
        if period == 'month':
            date_filter = "record_date >= date('now', 'start of month')"
        elif period == 'quarter':
            # Текущий квартал
            today = datetime.now()
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            quarter_start = today.replace(month=quarter_month, day=1)
            date_filter = f"record_date >= '{quarter_start.strftime('%Y-%m-%d')}'"
        elif period == 'last_month':
            date_filter = "record_date >= date('now', 'start of month', '-1 month') AND record_date < date('now', 'start of month')"
        elif period == 'last_quarter':
            today = datetime.now()
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            quarter_start = today.replace(month=quarter_month, day=1)
            last_quarter_start = quarter_start - timedelta(days=90)
            date_filter = f"record_date >= '{last_quarter_start.strftime('%Y-%m-%d')}' AND record_date < '{quarter_start.strftime('%Y-%m-%d')}'"
        else:
            date_filter = "1=1"
        
        # Формируем запрос
        if username:
            query = f'''
                SELECT 
                    COUNT(*) as тренировки,
                    SUM(distance) as дистанция,
                    SUM(duration) as время_минуты,
                    AVG(distance) as средняя_дистанция,
                    AVG(duration) as среднее_время
                FROM workouts 
                WHERE telegram_username = ? AND {date_filter}
            '''
            params = (username,)
        else:
            query = f'''
                SELECT 
                    telegram_username,
                    SUM(distance) as общая_дистанция,
                    SUM(duration) as общее_время,
                    COUNT(*) as тренировки
                FROM workouts 
                WHERE {date_filter}
                GROUP BY telegram_username
                ORDER BY общая_дистанция DESC
            '''
            params = ()
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def export_to_excel(self):
        """Экспорт данных в Excel"""
        conn = self.get_connection()
        
        with pd.ExcelWriter('database_export.xlsx', engine='openpyxl') as writer:
            # Экспорт никнеймов
            df_nicknames = pd.read_sql_query('SELECT * FROM nicknames', conn)
            df_nicknames.to_excel(writer, sheet_name='Никнеймы', index=False)
            
            # Экспорт тренировок
            df_workouts = pd.read_sql_query('SELECT * FROM workouts', conn)
            df_workouts.to_excel(writer, sheet_name='Тренировки', index=False)
        
        conn.close()
        return 'database_export.xlsx'
    
    def backup_database(self):
        """Создание резервной копии базы данных"""
        import shutil
        shutil.copy2(self.db_name, BACKUP_NAME)
        logger.info(f"Backup created: {BACKUP_NAME}")
    
    def restore_from_backup(self):
        """Восстановление из резервной копии"""
        import shutil
        shutil.copy2(BACKUP_NAME, self.db_name)
        logger.info(f"Database restored from {BACKUP_NAME}")
