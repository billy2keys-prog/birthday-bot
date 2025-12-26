"""
Telegram бот для дней рождения
Запускается через GitHub Actions каждый день в 9:00 МСК
"""

import os
import sys
import pandas as pd
import datetime
import requests

# ================= КОНФИГУРАЦИЯ =================
# Токен берется из секретов GitHub
TOKEN = os.getenv('7778232896:AAE3VzlNOwtNWJYkplZGrGORJIA7l0luM_w', '')

# ID администраторов (формат: "123456789,987654321")
ADMIN_IDS_STR = os.getenv('5638353159','1479958664')
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
        log(f"📂 Загрузка файла: {DATA_FILE}")
        
        if not os.path.exists(DATA_FILE):
            log("❌ Файл не найден!")
            return None
        
        # Читаем Excel
        df = pd.read_excel(DATA_FILE, engine='openpyxl')
        log(f"📊 Прочитано записей: {len(df)}")
        
        # Автоматически ищем нужные столбцы
        name_col = None
        date_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            
            # Столбец с именем
            if not name_col and any(word in col_lower for word in 
                                   ['фио', 'ф.и.о.', 'имя', 'позывной', 'сотрудник']):
                name_col = col
                log(f"✅ Найден столбец с именем: '{col}'")
            
            # Столбец с датой
            elif not date_col and any(word in col_lower for word in 
                                     ['дата', 'рожд', 'др', 'birthday', 'date']):
                date_col = col
                log(f"✅ Найден столбец с датой: '{col}'")
        
        # Если не нашли автоматически, берем первые два столбца
        if not name_col and len(df.columns) > 0:
            name_col = df.columns[0]
            log(f"⚠️  Авто-выбор столбца с именем: '{name_col}'")
        
        if not date_col and len(df.columns) > 1:
            date_col = df.columns[1]
            log(f"⚠️  Авто-выбор столбца с датой: '{date_col}'")
        
        if not name_col or not date_col:
            log("❌ Не удалось определить нужные столбцы")
            return None
        
        # Создаем чистый DataFrame
        df_clean = pd.DataFrame()
        df_clean['Позывной'] = df[name_col].astype(str).str.strip()
        df_clean['дата рождения'] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
        
        # Создаем личный номер
        df_clean['личный номер'] = [f"{i+1:03d}" for i in range(len(df_clean))]
        
        # Удаляем пустые записи
        initial_count = len(df_clean)
        df_clean = df_clean.dropna(subset=['дата рождения'])
        
        removed = initial_count - len(df_clean)
        if removed > 0:
            log(f"⚠️  Удалено {removed} записей без даты")
        
        log(f"✅ Валидных записей: {len(df_clean)}")
        return df_clean
        
    except Exception as e:
        log(f"❌ Ошибка загрузки: {str(e)}")
        return None

def find_birthdays(df, days_ahead=0):
    """Находит дни рождения в ближайшие дни."""
    if df is None or len(df) == 0:
        return []
    
    today = datetime.date.today()
    results = []
    
    for _, row in df.iterrows():
        birth_date = row['дата рождения'].date()
        
        # Дата рождения в текущем году
        birth_this_year = birth_date.replace(year=today.year)
        
        # Если день рождения уже прошел в этом году
        if birth_this_year < today:
            birth_this_year = birth_date.replace(year=today.year + 1)
        
        # Разница в днях
        days_diff = (birth_this_year - today).days
        
        # Проверяем, попадает ли в наш диапазон
        if 0 <= days_diff <= days_ahead:
            age = today.year - birth_date.year
            
            person = {
                'Позывной': str(row['Позывной']),
                'Дата рождения': birth_date.strftime('%d.%m.%Y'),
                'Личный номер': str(row['личный номер']),
                'Дней до ДР': days_diff,
                'Возраст': age
            }
            results.append(person)
    
    return results

def send_telegram_message(chat_id, text):
    """Отправляет сообщение в Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            log(f"❌ Ошибка отправки: {response.status_code}")
            return False
            
    except Exception as e:
        log(f"❌ Ошибка сети: {str(e)}")
        return False

# ================= ГЛАВНАЯ ФУНКЦИЯ =================

def main():
    """Основная функция, которая запускается каждый день."""
    log("=" * 50)
    log("🚀 ЗАПУСК ТЕЛЕГРАМ БОТА ЧЕРЕЗ GITHUB ACTIONS")
    log("=" * 50)
    
    # Проверяем конфигурацию
    if not TOKEN:
        log("❌ КРИТИЧЕСКАЯ ОШИБКА: Не установлен TELEGRAM_TOKEN")
        return
    
    if not ADMIN_IDS:
        log("❌ КРИТИЧЕСКАЯ ОШИБКА: Не установлены ADMIN_IDS")
        return
    
    log(f"👥 Получателей: {len(ADMIN_IDS)}")
    log(f"📅 Дата: {datetime.date.today().strftime('%d.%m.%Y')}")
    
    # Загружаем данные
    df = load_excel_data()
    if df is None:
        message = "❌ Не удалось загрузить данные из Excel файла"
        for user_id in ADMIN_IDS:
            send_telegram_message(user_id, message)
        return
    
    # Находим дни рождения
    birthdays_today = find_birthdays(df, 0)
    birthdays_tomorrow = find_birthdays(df, 1)
    birthdays_after_tomorrow = find_birthdays(df, 2)
    
    # Формируем даты
    today_str = datetime.date.today().strftime('%d.%m.%Y')
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    after_tomorrow = datetime.date.today() + datetime.timedelta(days=2)
    tomorrow_str = tomorrow.strftime('%d.%m.%Y')
    after_tomorrow_str = after_tomorrow.strftime('%d.%m.%Y')
    
    # Формируем сообщение
    message_lines = []
    message_lines.append(f"<b>⏰ Ежедневное уведомление о днях рождения</b>")
    message_lines.append(f"📅 Дата проверки: {today_str}")
    message_lines.append("")
    
    # Сегодня
    if birthdays_today:
        message_lines.append(f"🎉 <b>Сегодня ({today_str}) день рождения у:</b>")
        message_lines.append("")
        for person in birthdays_today:
            message_lines.append(f"• <b>{person['Позывной']}</b>")
            message_lines.append(f"  🎂 {person['Дата рождения']} ({person['Возраст']} лет)")
            message_lines.append(f"  🔢 №{person['Личный номер']}")
            message_lines.append("")
    else:
        message_lines.append(f"🎂 <b>Сегодня ({today_str}) дней рождения нет</b>")
        message_lines.append("")
    
    # Завтра
    if birthdays_tomorrow:
        message_lines.append(f"📅 <b>Завтра ({tomorrow_str}) день рождения у:</b>")
        message_lines.append("")
        for person in birthdays_tomorrow:
            message_lines.append(f"• <b>{person['Позывной']}</b>")
            message_lines.append(f"  🎂 {person['Дата рождения']} ({person['Возраст']} лет)")
            message_lines.append(f"  🔢 №{person['Личный номер']}")
            message_lines.append("")
    else:
        message_lines.append(f"📅 <b>Завтра ({tomorrow_str}) дней рождения нет</b>")
        message_lines.append("")
    
    # Послезавтра
    if birthdays_after_tomorrow:
        message_lines.append(f"📅 <b>Послезавтра ({after_tomorrow_str}) день рождения у:</b>")
        message_lines.append("")
        for person in birthdays_after_tomorrow:
            message_lines.append(f"• <b>{person['Позывной']}</b>")
            message_lines.append(f"  🎂 {person['Дата рождения']} ({person['Возраст']} лет)")
            message_lines.append(f"  🔢 №{person['Личный номер']}")
            message_lines.append("")
    else:
        message_lines.append(f"📅 <b>Послезавтра ({after_tomorrow_str}) дней рождения нет</b>")
    
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
        log(f"📨 Отправка пользователю {user_id}...")
        if send_telegram_message(user_id, message):
            success_count += 1
            log(f"  ✅ Успешно")
        else:
            log(f"  ❌ Ошибка")
    
    log(f"✅ Отправлено {success_count}/{len(ADMIN_IDS)} уведомлений")
    log("=" * 50)

if __name__ == "__main__":
    main()
