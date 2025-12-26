import os
import sys
import requests
from datetime import datetime, timedelta
import json

def handle_command(command, chat_id):
    """
    Обработчик команд бота
    """
    command = command.lower().strip()
    
    if command == "/start":
        message = "🚀 Бот запущен!\n\nДоступные команды:\n/today - задачи на сегодня\n/tomorrow - задачи на завтра\n/week - задачи на неделю"
    
    elif command == "/today":
        today = datetime.now().strftime("%d.%m.%Y")
        message = f"📅 Задачи на {today}:\n\n1. Проверить почту\n2. Созвоны с командой\n3. Дедлайн по проекту X"
    
    elif command == "/tomorrow":
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
        message = f"📅 Задачи на завтра ({tomorrow}):\n\n1. Подготовить отчет\n2. Встреча с клиентом\n3. Планирование спринта"
    
    elif command == "/week":
        message = "📊 Задачи на неделю:\n\nПн: Анализ метрик\nВт: Разработка фичи\nСр: Тестирование\nЧт: Деплой\nПт: Ретроспектива"
    
    else:
        message = f"❌ Неизвестная команда: {command}\n\nИспользуйте:\n/today\n/tomorrow\n/week"
    
    return {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

def send_to_telegram(message_data, bot_token):
    """
    Отправка сообщения в Telegram
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(url, json=message_data)
    return response.json()

if __name__ == "__main__":
    # Получаем данные из аргументов или переменных окружения
    try:
        # Для запуска из GitHub Actions
        if len(sys.argv) > 2:
            chat_id = sys.argv[1]
            command = sys.argv[2]
        else:
            # Для тестирования локально
            chat_id = os.getenv("CHAT_ID")
            command = os.getenv("COMMAND")
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not all([chat_id, command, bot_token]):
            print("Error: Missing required parameters")
            sys.exit(1)
        
        # Обрабатываем команду
        message_data = handle_command(command, chat_id)
        
        # Отправляем в Telegram
        result = send_to_telegram(message_data, bot_token)
        
        if result.get("ok"):
            print(f"✅ Сообщение отправлено пользователю {chat_id}")
        else:
            print(f"❌ Ошибка: {result}")
            
    except Exception as e:
        print(f"🔥 Критическая ошибка: {e}")
        sys.exit(1)
