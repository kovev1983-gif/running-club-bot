import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
from database import Database
from utils import *
import config
import os
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
WAITING_TRAINING, WAITING_NICKNAME = range(2)

# Инициализация базы данных
db = Database()

# Эмодзи для рейтинга
MEDALS = ["🥇", "🥈", "🥉"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
    🏃‍♂️ *Добро пожаловать в Беговой Клуб Бот!* 🏃‍♀️

    *Основные функции бота:*
    
    📝 *Записать тренировку* - запись дистанции и времени
    📊 *Статистика* - просмотр рейтингов и личной статистики
    🏷️ *Выбрать Ник* - установка уникального никнейма
    💾 *База данных* - экспорт данных (только для администраторов)
    
    *Формат записи тренировки:*
    `дистанция_км время_в_минутах`
    *Пример:* `10.5 90`
    
    *Приятных тренировок!* 💪
    """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def record_training_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало записи тренировки"""
    await update.message.reply_text(
        "📝 *Введите данные тренировки:*\n"
        "*Формат:* дистанция (км) и время (минуты) через пробел\n"
        "*Пример:* `10.5 90`\n\n"
        "⏰ *У вас есть 15 секунд на ввод*",
        parse_mode='Markdown'
    )
    return WAITING_TRAINING

async def handle_training_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода тренировки"""
    user_input = update.message.text
    username = update.message.from_user.username or str(update.message.from_user.id)
    
    distance, duration = validate_input(user_input)
    
    if distance is None or duration is None:
        await update.message.reply_text(
            "❌ *Неверный формат!*\n"
            "Введите данные в формате с пробелом между киллометрами и минутами:\n"
            "*Пример:* `12.5 90`",
            parse_mode='Markdown'
        )
        return WAITING_TRAINING
    
    # Сохраняем тренировку
    db.add_workout(username, distance, duration)
    
    await update.message.reply_text(
        f"✅ *Тренировка записана!*\n"
        f"*Дистанция:* {distance} км\n"
        f"*Время:* {duration} минут\n"
        f"*Средний темп:* {format_time(duration/distance)} мин/км",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Таймаут ввода"""
    await update.message.reply_text(
        "⏰ *Время ввода данных закончилось*\n"
        "Повторите пожалуйста или вернитесь в меню",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def statistics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню статистики"""
    keyboard = [
        [InlineKeyboardButton("📊 Рейтинг (все время)", callback_data='rating_all')],
        [InlineKeyboardButton("📈 Рейтинг (квартал)", callback_data='rating_quarter')],
        [InlineKeyboardButton("📅 Рейтинг (месяц)", callback_data='rating_month')],
        [InlineKeyboardButton("👤 Моя статистика", callback_data='my_stats')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 *Выберите отчет:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('rating_'):
        period = query.data.split('_')[1]
        await show_rating(query, period)
    elif query.data == 'my_stats':
        await show_my_stats_menu(query)
    elif query.data.startswith('stats_'):
        period = query.data.split('_')[1]
        await show_personal_stats(query, period)

async def show_rating(query, period):
    """Показ рейтинга"""
    if period == 'all':
        period_name = "за все время"
        df = db.get_statistics(period='all')
    elif period == 'quarter':
        period_name = "за текущий квартал"
        df = db.get_statistics(period='quarter')
    else:  # month
        period_name = "за текущий месяц"
        df = db.get_statistics(period='month')
    
    if df.empty:
        await query.edit_message_text(
            f"📊 *Рейтинг {period_name}*\n\n"
            f"Пока нет данных о тренировках 😔",
            parse_mode='Markdown'
        )
        return
    
    # Сортируем по дистанции
    df = df.sort_values('общая_дистанция', ascending=False)
    
    message = f"🏆 *Рейтинг {period_name}*\n\n"
    
    for i, (_, row) in enumerate(df.iterrows(), 1):
        username = row['telegram_username']
        nickname = db.get_nickname(username)
        display_name = nickname if nickname else f"@{username}"
        
        if i <= 3:
            medal = MEDALS[i-1] + " "
        else:
            medal = f"{i}. "
        
        total_km = row['общая_дистанция']
        total_minutes = row['общее_время']
        avg_pace = total_minutes / total_km if total_km > 0 else 0
        
        message += (
            f"{medal}*{display_name}*\n"
            f"   📏 {total_km:.1f} км | "
            f"⏱ {total_minutes//60}ч {total_minutes%60}м | "
            f"🏃 {format_time(avg_pace)} мин/км\n\n"
        )
    
    await query.edit_message_text(message, parse_mode='Markdown')

async def show_my_stats_menu(query):
    """Меню личной статистики"""
    keyboard = [
        [InlineKeyboardButton("Текущий месяц", callback_data='stats_month')],
        [InlineKeyboardButton("Прошлый месяц", callback_data='stats_last_month')],
        [InlineKeyboardButton("Текущий квартал", callback_data='stats_quarter')],
        [InlineKeyboardButton("Прошлый квартал", callback_data='stats_last_quarter')],
        [InlineKeyboardButton("За все время", callback_data='stats_all')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👤 *Выберите период для статистики:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_personal_stats(query, period):
    """Показ личной статистики"""
    username = query.from_user.username or str(query.from_user.id)
    nickname = db.get_nickname(username)
    display_name = nickname if nickname else f"@{username}"
    
    period_names = {
        'month': 'текущий месяц',
        'last_month': 'прошлый месяц',
        'quarter': 'текущий квартал',
        'last_quarter': 'прошлый квартал',
        'all': 'все время'
    }
    
    df = db.get_statistics(period=period, username=username)
    
    if df.empty or df.iloc[0]['тренировки'] == 0:
        await query.edit_message_text(
            f"📊 *Отчет по {display_name} за {period_names[period]}*\n\n"
            f"Нет данных о тренировках за этот период 😔",
            parse_mode='Markdown'
        )
        return
    
    data = df.iloc[0]
    
    message = (
        f"📊 *Отчет по {display_name} за {period_names[period]}*\n\n"
        f"1️⃣ *Количество тренировок:* {int(data['тренировки'])} тренировок\n"
        f"2️⃣ *Суммарная дистанция:* {data['дистанция']:.1f} км\n"
        f"3️⃣ *Средняя дистанция:* {data['средняя_дистанция']:.1f} км\n"
        f"4️⃣ *Длительность тренировок:* {format_duration(data['время_минуты'])}\n"
    )
    
    if data['дистанция'] > 0:
        avg_pace = data['время_минуты'] / data['дистанция']
        message += f"5️⃣ *Средняя скорость:* {format_time(avg_pace)} мин/км"
    
    await query.edit_message_text(message, parse_mode='Markdown')

async def choose_nick_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало выбора никнейма"""
    await update.message.reply_text(
        "🏷️ *Введите ваш никнейм:*\n"
        "Вы можете использовать любые символы и эмодзи\n\n"
        "⏰ *У вас есть 15 секунд на ввод*",
        parse_mode='Markdown'
    )
    return WAITING_NICKNAME

async def handle_nickname_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода никнейма"""
    nickname = update.message.text
    username = update.message.from_user.username or str(update.message.from_user.id)
    
    db.add_nickname(username, nickname)
    
    await update.message.reply_text(
        f"✅ *Никнейм установлен!*\n"
        f"Теперь вы будете отображаться как:\n"
        f"*{nickname}*",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def export_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт базы данных в Excel"""
    user_id = update.message.from_user.id
    
    # Проверка прав администратора
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ *Доступ запрещен*", parse_mode='Markdown')
        return
    
    try:
        filename = db.export_to_excel()
        
        with open(filename, 'rb') as file:
            await update.message.reply_document(
                document=file,
                caption="📁 *База данных экспортирована в Excel*",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Export error: {e}")
        await update.message.reply_text(
            f"❌ *Ошибка экспорта:* {str(e)}",
            parse_mode='Markdown'
        )

async def restore_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Восстановление из резервной копии"""
    user_id = update.message.from_user.id
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ *Доступ запрещен*", parse_mode='Markdown')
        return
    
    keyboard = [[
        InlineKeyboardButton("✅ Да", callback_data='restore_confirm'),
        InlineKeyboardButton("❌ Нет", callback_data='restore_cancel')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ *Вы точно уверены, что хотите восстановить данные?*\n"
        "*Текущая база данных будет удалена и заменена backup!*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def restore_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение восстановления"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'restore_confirm':
        try:
            db.restore_from_backup()
            await query.edit_message_text(
                "✅ *База данных успешно восстановлена из backup!*",
                parse_mode='Markdown'
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ *Ошибка восстановления:* {str(e)}",
                parse_mode='Markdown'
            )
    else:
        await query.edit_message_text(
            "❌ *Восстановление отменено*",
            parse_mode='Markdown'
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    await update.message.reply_text(
        "❌ *Операция отменена*",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

def main():
    """Запуск бота"""
    # Создание приложения
    application = Application.builder().token(config.TOKEN).build()
    
    # ConversationHandler для записи тренировки
    training_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('записать_тренировку', record_training_start)],
        states={
            WAITING_TRAINING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_training_input)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=15
    )
    
    # ConversationHandler для выбора никнейма
    nick_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('выбрать_ник', choose_nick_start)],
        states={
            WAITING_NICKNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nickname_input)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=15
    )
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(training_conv_handler)
    application.add_handler(nick_conv_handler)
    application.add_handler(CommandHandler("статистика", statistics_menu))
    application.add_handler(CommandHandler("database", export_database))
    application.add_handler(CommandHandler("backup", restore_backup))
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(rating_|my_stats|stats_)'))
    application.add_handler(CallbackQueryHandler(restore_confirmation, pattern='^restore_'))
    
    # Обработка таймаута
    application.add_handler(MessageHandler(filters.TEXT, timeout), group=1)
    
    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Запуск планировщика резервного копирования
    from backup import schedule_backup
    scheduler = schedule_backup()
    
    main()
