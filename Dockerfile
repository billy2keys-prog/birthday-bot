FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов
COPY requirements.txt .
COPY bot.py .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Создаем пустой Excel файл (будет заменен вашим)
RUN touch Штат_чистый.xlsx

# Запуск бота
CMD ["python", "bot.py"]
