"""
Telegram бот для дней рождения с командами
Запускается через GitHub Actions каждый день в 9:00 МСК
"""

import os
import sys
import pandas as pd
import datetime
import requests
import json

# ================= КОНФИГУРАЦИЯ =================
# Токен берется из секретов GitHub
TOKEN = os.getenv('TELEGRAM_TOKEN', '')

# ID администраторов (формат: "123456789,987654321")
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',') if id.strip()]

# Файл с данными
DATA_FILE = 'Штат_чистый.xlsx'

# ================= ЛОГИРОВАНИЕ =================
def log(message):
    """Простое логирование в консоль GitHub Actions."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] {message}')
    sys.stdout.flush()

# ================= ОСНОВНЫЕ ФУНКЦИИ =================

def load_excel_data():
    """Загружает данные из Excel файла."""
    try:
        if not os.path.exists(DATA_FILE):
            return None
        
        # Читаем Excel
        df = pd.read_excel(DATA_FILE, engine='openpyxl')
        
        # Автоматически ищем нужные столбцы
        name_col = None
        date_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            
            if not name_col and any(word in col_lower for word in 
                                   ['фио', 'ф.и.о.', 'имя', 'позывной', 'сотрудник']):
                name_col = col
                
            if not date_col and any(word in col_lower for word in 
                                   ['дата', 'рожд', 'др', 'birthday', 'date']):
                date_col = col
        
        # Если не нашли автоматически, берем первые два столбца
        if not name_col and len(df.columns) > 0:
            name_col = df.columns[0]
        
        if not date_col and len(df.columns) > 1:
            date_col = df.columns[1]
        
        if not name_col or not date_col:
            return None
        
        # Создаем чистый DataFrame
        df_clean = pd.DataFrame()
        df_clean['Позывной'] = df[name_col].astype(str).str.strip()
        df_clean['дата рождения'] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
        
        # Создаем личный номер
        df_clean['личный номер'] = [f"{i+1:03d}" for i in range(len(df_clean))]
        
        # Удаляем пустые записи
        df_clean = df_clean.dropna(subset=['дата рождения'])
        
        return df_clean
        
    except Exception as e:
        return None

def find_birthdays(df, days_ahead=0):
    """Находит дни рождения в ближайшие дни."""
    if df is None or len(df) == 0:
        return []
    
    today = datetime.date.today()
    results = []
    
    for _, row in df.iterrows():
        birth_date = row['дата рождения'].date()
        birth_this_year = birth_date.replace(year=today.year)
        
        if birth_this_year < today:
            birth_this_year = birth_date.replace(year=today.year + 1)
        
        days_diff = (birth_this_year - today).days
        
        if 0 <= days_diff <= days_ahead:
            age = today.year - birth_date.year
            
            person = {
                'Позывной': row['Позывной'],
                'Дата рождения': birth_date.strftime('%d.%m.%Y'),
                'Личный номер': row['личный номер'],
                'Возраст': age,
                'Дней до ДР': days_diff
            }
            results.append(person)
    
    return results

def send_telegram_message(chat_id, text, reply_markup=None):
    """Отправляет сообщение в Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        response = requests.post(url, json=data, timeout=10)
        return response.json()
        
    except Exception as e:
        return {'ok': False, 'description': str(e)}

def process_command(chat_id, command):
    """Обрабатывает команды от пользователя."""
    df = load_excel_data()
    
    if df is None:
        return "❌ Не удалось загрузить данные из Excel файла"
    
    today_str = datetime.date.today().strftime('%d.%m.%Y')
    tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    after_tomorrow_str = (datetime.date.today() + datetime.timedelta(days=2)).strftime('%d.%m.%Y')
    
    if command == '/start':
        response = (
            "👋 <b>Бот для дней рождения сотрудников</b>\n\n"
            "📁 Работает с Excel файлом\n"
            "⏰ Авто-уведомления в 9:00 каждый день\n\n"
            "<b>📋 Команды:</b>\n"
            "/today - дни рождения сегодня\n"
            "/tomorrow - дни рождения завтра\n"
            "/after_tomorrow - дни рождения послезавтра\n"
            "/all - все дни рождения\n"
            "/help - справка\n\n"
            "💬 <b>Вопросы:</b>\n"
            "• Когда кончится война?\n"
            "• Когда кончится СВО?"
        )
        
    elif command == '/today' or command == 'сегодня':
        birthdays = find_birthdays(df, 0)
        
        if birthdays:
            response = f"🎉 <b>Сегодня ({today_str}) день рождения у:</b>\n\n"
            for person in birthdays:
                response += f"• <b>{person['Позывной']}</b>\n"
                response += f"  🎂 {person['Дата рождения']} ({person['Возраст']} лет)\n"
                response += f"  🔢 №{person['Личный номер']}\n\n"
            response += f"<i>Всего: {len(birthdays)} человек</i>"
        else:
            response = f"🎂 <b>Сегодня ({today_str}) дней рождения нет</b>"
    
    elif command == '/tomorrow' or command == 'завтра':
        birthdays = find_birthdays(df, 1)
        
        if birthdays:
            response = f"🎉 <b>Завтра ({tomorrow_str}) день рождения у:</b>\n\n"
            for person in birthdays:
                response += f"• <b>{person['Позывной']}</b>\n"
                response += f"  🎂 {person['Дата рождения']} ({person['Возраст']} лет)\n"
                response += f"  🔢 №{person['Личный номер']}\n\n"
            response += f"<i>Всего: {len(birthdays)} человек</i>"
        else:
            response = f"🎂 <b>Завтра ({tomorrow_str}) дней рождения нет</b>"
    
    elif command == '/after_tomorrow' or command == 'послезавтра':
        birthdays = find_birthdays(df, 2)
        
        if birthdays:
            response = f"🎉 <b>Послезавтра ({after_tomorrow_str}) день рождения у:</b>\n\n"
            for person in birthdays:
                response += f"• <b>{person['Позывной']}</b>\n"
                response += f"  🎂 {person['Дата рождения']} ({person['Возраст']} лет)\n"
                response += f"  🔢 №{person['Личный номер']}\n\n"
            response += f"<i>Всего: {len(birthdays)} человек</i>"
        else:
            response = f"🎂 <b>Послезавтра ({after_tomorrow_str}) дней рождения нет</b>"
    
    elif command == '/all' or command == 'все':
        # Сортируем по дате рождения
        df_sorted = df.copy()
        df_sorted['month_day'] = df_sorted['дата рождения'].dt.strftime('%m-%d')
        df_sorted = df_sorted.sort_values('month_day')
        
        response = "📋 <b>Все дни рождения (сортировка по дате):</b>\n\n"
        
        current_month = None
        month_names = {
            1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
            5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
            9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
        }
        
        count = 0
        for _, row in df_sorted.iterrows():
            birth_date = row['дата рождения'].date()
            birth_month = birth_date.month
            
            if birth_month != current_month:
                current_month = birth_month
                response += f"\n<b>────── {month_names[birth_month]} ──────</b>\n"
            
            age = datetime.date.today().year - birth_date.year
            response += f"• <b>{row['Позывной']}</b>\n"
            response += f"  {birth_date.strftime('%d.%m.%Y')} ({age} лет)\n"
            response += f"  №{row['личный номер']}\n"
            
            count += 1
            
            if len(response) > 3000:
                response += "\n... (сообщение обрезано)"
                break
        
        response += f"\n\n<i>Всего записей: {count}</i>"
    
    elif command == '/help' or command == 'помощь':
        response = (
            "📖 <b>Справка по командам:</b>\n\n"
            "<b>Основные команды:</b>\n"
            "/today - дни рождения сегодня\n"
            "/tomorrow - дни рождения завтра\n"
            "/after_tomorrow - дни рождения послезавтра\n"
            "/all - все дни рождения\n"
            "/help - эта справка\n\n"
            "<b>Также можно писать словами:</b>\n"
            "• \"сегодня\" - дни рождения сегодня\n"
            "• \"завтра\" - дни рождения завтра\n"
            "• \"послезавтра\" - дни рождения послезавтра\n"
            "• \"все\" - все дни рождения\n\n"
            "<b>Вопросы:</b>\n"
            "• \"Когда кончится война?\"\n"
            "• \"Когда кончится СВО?\""
        )
    
    elif 'война' in command.lower():
        response = "🇷🇺 У нас не ведется войны"
    
    elif 'сво' in command.lower():
        response = "🇷🇺 Завтра"
    
    elif any(word in command.lower() for word in ['привет', 'здравствуй', 'hello', 'hi']):
        import random
        greetings = ["Привет! 👋", "Здравствуйте! 😊", "Добрый день! ☀️"]
        response = random.choice(greetings)
    
    else:
        response = (
            "Неизвестная команда 😕\n\n"
            "Используйте:\n"
            "/today - дни рождения сегодня\n"
            "/tomorrow - дни рождения завтра\n"
            "/after_tomorrow - дни рождения послезавтра\n"
            "/all - все дни рождения\n"
            "/help - справка"
        )
    
    return response

def create_keyboard():
    """Создает клавиатуру с кнопками."""
    keyboard = {
        'keyboard': [
            ['/today', '/tomorrow'],
            ['/after_tomorrow', '/all'],
            ['/help']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }
    return keyboard

# ================= ГЛАВНАЯ ФУНКЦИЯ ДЛЯ ЕЖЕДНЕВНЫХ УВЕДОМЛЕНИЙ =================

def send_daily_notifications():
    """Отправляет ежедневные уведомления."""
    log("=" * 50)
    log("⏰ Отправка ежедневных уведомлений...")
    
    df = load_excel_data()
    if df is None:
        log("❌ Не удалось загрузить данные")
        return
    
    # Находим дни рождения
    birthdays_today = find_birthdays(df, 0)
    birthdays_tomorrow = find_birthdays(df, 1)
    birthdays_after_tomorrow = find_birthdays(df, 2)
    
    today_str = datetime.date.today().strftime('%d.%m.%Y')
    tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    after_tomorrow_str = (datetime.date.today() + datetime.timedelta(days=2)).strftime('%d.%m.%Y')
    
    # Формируем сообщение
    message_lines = []
    message_lines.append(f"<b>⏰ Ежедневное уведомление о днях рождения</b>")
    message_lines.append(f"📅 Дата проверки: {today_str}")
    message_lines.append("")
    
    # Сегодня
    if birthdays_today:
        message_lines.append(f"🎉 <b>Сегодня ({today_str}):</b>\n")
        for person in birthdays_today:
            message_lines.append(f"• {person['Позывной']} ({person['Возраст']} лет)")
            message_lines.append(f"  №{person['Личный номер']}\n")
    else:
        message_lines.append(f"🎂 <b>Сегодня ({today_str}) нет дней рождения</b>\n")
    
    # Завтра
    if birthdays_tomorrow:
        message_lines.append(f"📅 <b>Завтра ({tomorrow_str}):</b>\n")
        for person in birthdays_tomorrow:
            message_lines.append(f"• {person['Позывной']} ({person['Возраст']} лет)")
            message_lines.append(f"  №{person['Личный номер']}\n")
    else:
        message_lines.append(f"📅 <b>Завтра ({tomorrow_str}) нет дней рождения</b>\n")
    
    # Послезавтра
    if birthdays_after_tomorrow:
        message_lines.append(f"📅 <b>Послезавтра ({after_tomorrow_str}):</b>\n")
        for person in birthdays_after_tomorrow:
            message_lines.append(f"• {person['Позывной']} ({person['Возраст']} лет)")
            message_lines.append(f"  №{person['Личный номер']}\n")
    else:
        message_lines.append(f"📅 <b>Послезавтра ({after_tomorrow_str}) нет дней рождения</b>")
    
    # Статистика
    message_lines.append("")
    message_lines.append("<b>📊 Статистика:</b>")
    message_lines.append(f"• Сегодня: {len(birthdays_today)} чел.")
    message_lines.append(f"• Завтра: {len(birthdays_tomorrow)} чел.")
    message_lines.append(f"• Послезавтра: {len(birthdays_after_tomorrow)} чел.")
    message_lines.append(f"• Всего в базе: {len(df)} чел.")
    
    message = "\n".join(message_lines)
    
    # Отправляем всем администраторам
    success_count = 0
    for user_id in ADMIN_IDS:
        result = send_telegram_message(user_id, message)
        if result and result.get('ok'):
            success_count += 1
            log(f"✅ Отправлено пользователю {user_id}")
        else:
            log(f"❌ Ошибка отправки {user_id}: {result.get('description', 'Unknown error')}")
    
    log(f"📨 Отправлено {success_count}/{len(ADMIN_IDS)} уведомлений")
    log("=" * 50)

# ================= WEBHOOK ОБРАБОТЧИК =================

def handle_webhook_update(update):
    """Обрабатывает обновление от Telegram webhook."""
    try:
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            
            log(f"📩 Получено сообщение от {chat_id}: {text}")
            
            # Обрабатываем команду
            response = process_command(chat_id, text)
            
            # Отправляем ответ
            send_telegram_message(chat_id, response)
            
        elif 'callback_query' in update:
            # Обработка нажатий на кнопки
            callback = update['callback_query']
            chat_id = callback['message']['chat']['id']
            data = callback['data']
            
            response = process_command(chat_id, data)
            send_telegram_message(chat_id, response)
            
    except Exception as e:
        log(f"❌ Ошибка обработки сообщения: {e}")

# ================= ОСНОВНАЯ ФУНКЦИЯ =================

def main():
    """Основная функция, которая запускается каждый день."""
    log("=" * 50)
    log("🚀 ЗАПУСК ТЕЛЕГРАМ БОТА")
    log("=" * 50)
    
    # Проверяем конфигурацию
    if not TOKEN:
        log("❌ КРИТИЧЕСКАЯ ОШИБКА: Не установлен TELEGRAM_TOKEN")
        return
    
    if not ADMIN_IDS:
        log("❌ КРИТИЧЕСКАЯ ОШИБКА: Не установлены ADMIN_IDS")
        return
    
    log(f"✅ Получателей: {len(ADMIN_IDS)}")
    
    # Проверяем, это webhook или расписание
    # Если есть данные от webhook - обрабатываем
    # Если нет - отправляем ежедневные уведомления
    
    try:
        # Проверяем, есть ли данные от webhook
        if len(sys.argv) > 1:
            # Это вызов от webhook
            update_data = sys.argv[1]
            update = json.loads(update_data)
            handle_webhook_update(update)
        else:
            # Это ежедневный запуск по расписанию
            send_daily_notifications()
            
    except Exception as e:
        log(f"❌ Ошибка в main: {e}")

if __name__ == "__main__":
    main()
