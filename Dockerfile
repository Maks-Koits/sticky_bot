FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev && \
    pip install --upgrade pip && \
    pip install aiogram==3.0.0 python-dotenv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY bot.py /app/
COPY .env /app/

CMD ["python", "bot.py"]