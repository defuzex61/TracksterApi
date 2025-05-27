FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential libopenblas-dev libgomp1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект, включая папку src
COPY . .

# Запуск приложения (обрати внимание на путь к модулю)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]