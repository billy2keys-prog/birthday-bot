#!/usr/bin/env python3
"""
🎂 Birthday Bot с чтением Excel файла "Штат_чистый.xlsx"
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import schedule
import time
import threading
import logging
import telebot
import re

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '')
EXCEL_FILE = "Штат_чистый.xlsx"
NOTIFICATION_TIME = "09:00"  # 09:00 утра по UTC

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== РАБОТА С EXCEL ==================
def load_excel_data():
    """Загрузить данные из Excel файла"""
    try:
        # Пробуем разные возможные названия листов
        sheet_names = pd.ExcelFile(EXCEL_FILE).sheet_names
        logger.info(f"Найденные листы: {sheet_names}")
        
        # Пробуем прочитать первый лист или ищем по ключевым словам
        for sheet in sheet_names:
            try:
                df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
                logger.info(f"Лист '{sheet}': {len(df)} строк, {len(df.columns)} колонок")
                
                # Ищем колонки с ФИО и датой рождения
                fio_columns = []
                date_columns = []
                
                for col in df.columns:
                    col_str = str(col).lower()
                    
                    # Ищем колонки с ФИО
                    if any(word in col_str for word in ['фио', 'ф.и.о', 'имя', 'name', 'сотрудник']):
                        fio_columns.append(col)
                    
                    # Ищем колонки с датой рождения
                    if any(word in col_str for word in ['дата', 'др', 'birth', 'рожден']):
                        date_columns.append(col)
                
                logger.info(f"Найдены колонки ФИО: {fio_columns}")
                logger.info(f"Найдены колонки дат: {date_columns}")
                
                if fio_columns and date_columns:
                    # Берем первую найденную колонку каждого типа
                    fio_col = fio_columns[0]
                    date_col = date_columns[0]
                    
                    logger.info(f"Используем колонки: ФИО='{fio_col}', Дата='{date_col}'")
                    
                    # Создаем список людей
                    people = []
                    
                    for idx, row in df.iterrows():
                        try:
                            name = str(row[fio_col]).strip()
                            date_str = str(row[date_col]).strip()
                            
                            # Пропускаем пустые строки
                            if pd.isna(name) or name == 'nan' or not name:
                                continue
                            
                            # Пытаемся преобразовать дату
                            birthday = None
                            
                            # Пробуем разные форматы дат
                            if not pd.isna(date_str) and date_str != 'nan':
                                try:
                                    # Пробуем парсить как datetime
                                    if isinstance(date_str, str):
                                        # Убираем лишние пробелы и время если есть
                                        date_str_clean = date_str.split()[0] if ' ' in date_str else date_str
                                        
                                        # Пробуем разные форматы
                                        for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%y']:
                                            try:
                                                birthday = datetime.strptime(date_str_clean, fmt)
                                                break
                                            except:
                                                continue
                                    
                                    # Если date_str уже datetime
                                    elif isinstance(date_str, pd.Timestamp):
                                        birthday = date_str.to_pydatetime()
                                    elif isinstance(date_str, datetime):
                                        birthday = date_str
                                    
                                except Exception as e:
                                    logger.warning(f"Не удалось распарсить дату '{date_str}' для {name}: {e}")
                                    birthday = None
                            
                            people.append({
                                'name': name,
                                'birthday': birthday,
                                'row': idx + 2  # +2 потому что Excel нумерация с 1 и заголовок
                            })
                            
                        except Exception as e:
                            logger.warning(f"Ошибка в строке {idx}: {e}")
                            continue
                    
                    logger.info(f"Загружено {len(people)} человек из Excel")
                    return people, df, fio_col, date_col
                
            except Exception as e:
                logger.error(f"Ошибка чтения листа '{sheet}': {e}")
                continue
        
        logger.error("Не удалось найти подходящие колонки в Excel файле")
        return [], None, None, None
        
    except Exception as e:
        logger.error(f"Ошибка загрузки Excel файла: {e}")
        return [], None, None, None

def get_today_birthdays():
    """Получить дни рождения на сегодня"""
    people, _, _, _ = load_excel_data()
    today = datetime.now()
    
    result = []
    for person in people:
        if person['birthday']:
            # Сравниваем только день и месяц
            if (person['birthday'].month == today.month and 
                person['birthday'].day == today.day):
                
                # Вычисляем возраст
                age = today.year - person['birthday'].year
                result.append({
                    'name': person['name'],
                    'birthday': person['birthday'],
                    'age': age
                })
    
    return result

def get_tomorrow_birthdays():
    """Получить дни рождения на завтра"""
    people, _, _, _ = load_excel_data()
    tomorrow = datetime.now() + timedelta(days=1)
    
    result = []
    for person in people:
        if person['birthday']:
            if (person['birthday'].month == tomorrow.month and 
                person['birthday'].day == tomorrow.day):
                
                age = tomorrow.year - person['birthday'].year
                result.append({
                    'name': person['name'],
                    'birthday': person['birthday'],
                    'age': age
                })
    
    return result

def get_after_tomorrow_birthdays():
    """Получить дни рождения на послезавтра"""
    people, _, _, _ = load_excel_data()
    after_tomorrow = datetime.now() + timedelta(days=2)
    
    result = []
    for person in people:
        if person['birthday']:
            if (person['birthday'].month == after_tomorrow.month and 
                person['birthday'].day == after_tomorrow.day):
                
                age = after_tomorrow.year - person['birthday'].year
                result.append({
                    'name': person['name'],
                    'birthday': person['birthday'],
                    'age': age
                })
    
    return result

def get_upcoming_birthdays(days=7):
    """Получить ближайшие дни рождения"""
    people, _, _, _ = load_excel_data()
    today = datetime.now()
    
    result = []
    for i in range(days):
        check_date = today + timedelta(days=i)
        
        for person in people:
            if person['birthday']:
                if (person['birthday'].month == check_date.month and 
                    person['birthday'].day == check_date.day):
                    
                    age = check_date.year - person['birthday'].year
                    result.append({
                        'name': person['name'],
                        'birthday': person['birthday'],
                        'age': age,
                        'days_until': i
                    })
    
    # Сортируем по количеству дней до ДР
    result.sort(key=lambda x: x['days_until'])
    return result

# ================== ФОРМАТИРОВАНИЕ ==================
def format_age(age):
    """Правильное склонение лет"""
    if age % 10 == 1 and age % 100 != 11:
        return f"{age} год"
    elif 2 <= age % 10 <= 4 and (age % 100 < 10 or age % 100 >= 20):
        return f"{age} года"
    else:
        return f"{age} лет"

def format_birthday_list(birthdays, day_offset=0):
    """Форматировать список дней рождения"""
    if not birthdays:
        return "нет"
    
    lines = []
    for b in birthdays:
        age_text = format_age(b['age'])
        lines.append(f"• {b['name']} ({age_text})")
    
    return "\n".join(lines)

# ================== КОМАНДЫ БОТА ==================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Команда /start"""
    # Загружаем данные для статистики
    people, df, fio_col, date_col = load_excel_data()
    
    if df is not None:
        total_people = len(people)
        people_with_dates = len([p for p in people if p['birthday']])
        
        stats = f"📊 *Статистика из Excel:*\n"
        stats += f"• Всего записей: {total_people}\n"
        stats += f"• С указанной датой рождения: {people_with_dates}\n"
        stats += f"• Колонка ФИО: '{fio_col}'\n"
        stats += f"• Колонка дат: '{date_col}'\n\n"
    else:
        stats = "⚠️ *Файл Excel не найден или не распознан*\n\n"
    
    welcome = f"""
🎂 *Birthday Bot для Excel файла*

{stats}
*Команды:*
/today - Дни рождения сегодня
/tomorrow - Дни рождения завтра
/after_tomorrow - Дни рождения послезавтра
/week - Ближайшие 7 дней
/all - Все дни рождения (только с датами)
/count - Статистика по файлу
/debug - Отладочная информация

*Автоматически:* Ежедневно в 09:00 отправляется отчет.
    """
    
    bot.reply_to(message, welcome, parse_mode='Markdown')

@bot.message_handler(commands=['today'])
def today_command(message):
    """Дни рождения сегодня"""
    birthdays = get_today_birthdays()
    today = datetime.now().strftime('%d.%m.%Y')
    
    if birthdays:
        msg = f"🎂 *Сегодня ({today}) день рождения у:*\n\n"
        msg += format_birthday_list(birthdays)
    else:
        msg = f"✅ Сегодня ({today}) дней рождения нет!"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['tomorrow'])
def tomorrow_command(message):
    """Дни рождения завтра"""
    birthdays = get_tomorrow_birthdays()
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
    
    if birthdays:
        msg = f"🎁 *Завтра ({tomorrow}) день рождения у:*\n\n"
        msg += format_birthday_list(birthdays)
    else:
        msg = f"✅ Завтра ({tomorrow}) дней рождения нет!"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['after_tomorrow', 'послезавтра'])
def after_tomorrow_command(message):
    """Дни рождения послезавтра"""
    birthdays = get_after_tomorrow_birthdays()
    after_tomorrow = (datetime.now() + timedelta(days=2)).strftime('%d.%m.%Y')
    
    if birthdays:
        msg = f"📅 *Послезавтра ({after_tomorrow}) день рождения у:*\n\n"
        msg += format_birthday_list(birthdays)
    else:
        msg = f"✅ Послезавтра ({after_tomorrow}) дней рождения нет!"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['week'])
def week_command(message):
    """Ближайшие 7 дней"""
    upcoming = get_upcoming_birthdays(7)
    
    if not upcoming:
        msg = "✅ В ближайшие 7 дней дней рождения нет!"
    else:
        msg = "📅 *Ближайшие дни рождения (7 дней):*\n\n"
        
        # Группируем по дням
        by_day = {}
        for b in upcoming:
            day = b['days_until']
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(b)
        
        # Формируем сообщение по дням
        for day in sorted(by_day.keys()):
            date = datetime.now() + timedelta(days=day)
            
            if day == 0:
                day_text = "🎂 СЕГОДНЯ"
            elif day == 1:
                day_text = "🎁 ЗАВТРА"
            elif day == 2:
                day_text = "📅 ПОСЛЕЗАВТРА"
            else:
                day_text = f"📅 {date.strftime('%d.%m')} (через {day} дней)"
            
            msg += f"{day_text}:\n"
            
            for b in by_day[day]:
                age_text = format_age(b['age'])
                msg += f"  • {b['name']} ({age_text})\n"
            
            msg += "\n"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['all'])
def all_command(message):
    """Все дни рождения из файла"""
    people, _, _, _ = load_excel_data()
    
    # Фильтруем только тех, у кого есть дата рождения
    people_with_birthdays = [p for p in people if p['birthday']]
    
    if not people_with_birthdays:
        msg = "📭 В файле нет записей с датами рождения"
    else:
        # Сортируем по дате рождения (игнорируя год)
        people_with_birthdays.sort(key=lambda x: (x['birthday'].month, x['birthday'].day))
        
        msg = "📋 *Все дни рождения из файла:*\n\n"
        
        current_month = None
        for person in people_with_birthdays:
            month = person['birthday'].month
            
            if month != current_month:
                current_month = month
                month_name = person['birthday'].strftime('%B')  # Название месяца
                msg += f"*{month_name.upper()}:*\n"
            
            age = datetime.now().year - person['birthday'].year
            age_text = format_age(age)
            date_str = person['birthday'].strftime('%d.%m')
            
            msg += f"• {person['name']} - {date_str} ({age_text})\n"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['count'])
def count_command(message):
    """Статистика по файлу"""
    people, df, fio_col, date_col = load_excel_data()
    
    if df is None:
        msg = "❌ Файл Excel не найден или поврежден"
    else:
        total_rows = len(df)
        total_people = len(people)
        people_with_dates = len([p for p in people if p['birthday']])
        
        msg = f"📊 *Статистика файла:*\n\n"
        msg += f"• Файл: `{EXCEL_FILE}`\n"
        msg += f"• Всего строк: {total_rows}\n"
        msg += f"• Распознано людей: {total_people}\n"
        msg += f"• С датой рождения: {people_with_dates}\n"
        
        if fio_col and date_col:
            msg += f"• Колонка ФИО: `{fio_col}`\n"
            msg += f"• Колонка дат: `{date_col}`\n"
        
        # Самые близкие дни рождения
        upcoming = get_upcoming_birthdays(30)[:5]  # Ближайшие 5 ДР в течение месяца
        if upcoming:
            msg += f"\n*Ближайшие дни рождения:*\n"
            for b in upcoming:
                date = datetime.now() + timedelta(days=b['days_until'])
                age_text = format_age(b['age'])
                msg += f"• {b['name']} - {date.strftime('%d.%m')} ({age_text})\n"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['debug'])
def debug_command(message):
    """Отладочная информация"""
    people, df, fio_col, date_col = load_excel_data()
    
    if df is None:
        msg = "❌ Файл не найден"
    else:
        msg = f"🔍 *Отладочная информация:*\n\n"
        msg += f"• Файл: {EXCEL_FILE}\n"
        msg += f"• Размер: {os.path.getsize(EXCEL_FILE) / 1024:.1f} KB\n"
        msg += f"• Листы: {df.sheet_names if hasattr(df, 'sheet_names') else 'N/A'}\n"
        
        if hasattr(df, 'columns'):
            msg += f"\n*Колонки в DataFrame:*\n"
            for i, col in enumerate(df.columns):
                msg += f"{i+1}. `{col}`\n"
        
        if people:
            msg += f"\n*Первые 5 записей:*\n"
            for i, person in enumerate(people[:5]):
                birthday_str = person['birthday'].strftime('%d.%m.%Y') if person['birthday'] else 'НЕТ'
                msg += f"{i+1}. {person['name']} - {birthday_str}\n"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

# ================== АВТОМАТИЧЕСКИЕ УВЕДОМЛЕНИЯ ==================
def send_daily_notification():
    """Отправить ежедневное уведомление"""
    try:
        logger.info("Отправка ежедневного уведомления...")
        
        today = datetime.now()
        today_str = today.strftime('%d.%m.%Y')
        
        # Получаем данные
        today_birthdays = get_today_birthdays()
        tomorrow_birthdays = get_tomorrow_birthdays()
        after_tomorrow_birthdays = get_after_tomorrow_birthdays()
        
        # Формируем сообщение
        msg = f"📅 *Ежедневный отчет о днях рождения*\n"
        msg += f"*Дата:* {today_str}\n\n"
        
        # Сегодня
        if today_birthdays:
            msg += "🎂 *СЕГОДНЯ:*\n"
            msg += format_birthday_list(today_birthdays)
            msg += "\n\n"
        else:
            msg += "✅ *Сегодня дней рождения нет*\n\n"
        
        # Завтра
        if tomorrow_birthdays:
            msg += "🎁 *ЗАВТРА:*\n"
            msg += format_birthday_list(tomorrow_birthdays)
            msg += "\n\n"
        else:
            msg += "✅ *Завтра дней рождения нет*\n\n"
        
        # Послезавтра
        if after_tomorrow_birthdays:
            msg += "📅 *ПОСЛЕЗАВТРА:*\n"
            msg += format_birthday_list(after_tomorrow_birthdays)
            msg += "\n\n"
        else:
            msg += "✅ *Послезавтра дней рождения нет*\n\n"
        
        msg += "_Используйте /today для деталей_"
        
        # Отправляем админу
        if ADMIN_CHAT_ID:
            try:
                bot.send_message(ADMIN_CHAT_ID, msg, parse_mode='Markdown')
                logger.info(f"Уведомление отправлено админу {ADMIN_CHAT_ID}")
            except Exception as e:
                logger.error(f"Ошибка отправки админу: {e}")
        
        logger.info("Ежедневное уведомление сформировано")
        
    except Exception as e:
        logger.error(f"Ошибка в send_daily_notification: {e}")

def schedule_checker():
    """Запуск планировщика"""
    schedule.every().day.at(NOTIFICATION_TIME).do(send_daily_notification)
    
    logger.info(f"Планировщик запущен. Уведомления в {NOTIFICATION_TIME} UTC")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# ================== ЗАПУСК БОТА ==================
def main():
    """Основная функция"""
    logger.info("🚀 Запуск Excel Birthday Bot...")
    
    # Проверяем наличие Excel файла
    if not os.path.exists(EXCEL_FILE):
        logger.error(f"Файл {EXCEL_FILE} не найден!")
        if ADMIN_CHAT_ID:
            bot.send_message(ADMIN_CHAT_ID, 
                           f"❌ Файл `{EXCEL_FILE}` не найден!\n"
                           "Загрузите его в корень репозитория.")
        return
    
    # Загружаем данные
    people, df, fio_col, date_col = load_excel_data()
    
    if df is not None:
        logger.info(f"Загружено {len(people)} записей из Excel")
        
        # Отправляем сообщение админу о запуске
        if ADMIN_CHAT_ID:
            try:
                bot.send_message(
                    ADMIN_CHAT_ID,
                    f"✅ *Excel Birthday Bot запущен!*\n\n"
                    f"📊 Загружено: {len(people)} записей\n"
                    f"⏰ Уведомления: каждый день в {NOTIFICATION_TIME} UTC\n"
                    f"📅 Ближайшие ДР: {len(get_upcoming_birthdays(7))} в ближайшие 7 дней",
                    parse_mode='Markdown'
                )
            except:
                pass
    
    # Запускаем планировщик
    scheduler_thread = threading.Thread(target=schedule_checker, daemon=True)
    scheduler_thread.start()
    
    logger.info("Бот готов к работе. Ожидание команд...")
    
    # Запускаем бота
    bot.infinity_polling()

if __name__ == "__main__":
    main()
