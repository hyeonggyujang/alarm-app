# FROM arm32v7/python:3.10-slim
#for local testing
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    alsa-utils \
    libsdl2-mixer-2.0-0 \
    libsdl2-2.0-0 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

ENV SDL_AUDIODRIVER=alsa
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]