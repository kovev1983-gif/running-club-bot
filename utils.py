from datetime import datetime

def format_time(minutes_total):
    """Форматирование времени в минуты:секунды"""
    minutes = int(minutes_total)
    seconds = int((minutes_total - minutes) * 60)
    return f"{minutes}:{seconds:02d}"

def format_duration(minutes):
    """Форматирование продолжительности"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours} часов {mins} минут"

def get_current_quarter():
    """Получение текущего квартала"""
    month = datetime.now().month
    return (month - 1) // 3 + 1

def get_quarter_dates(quarter=None, year=None):
    """Получение дат начала и конца квартала"""
    if year is None:
        year = datetime.now().year
    if quarter is None:
        quarter = get_current_quarter()
    
    quarter_start_month = (quarter - 1) * 3 + 1
    quarter_end_month = quarter_start_month + 2
    
    start_date = datetime(year, quarter_start_month, 1)
    if quarter_end_month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, quarter_end_month + 1, 1)
    
    return start_date, end_date

def validate_input(text):
    """Проверка формата ввода тренировки"""
    try:
        parts = text.split()
        if len(parts) != 2:
            return None, None
        
        distance = float(parts[0])
        duration = int(parts[1])
        
        return distance, duration
    except:
        return None, None
