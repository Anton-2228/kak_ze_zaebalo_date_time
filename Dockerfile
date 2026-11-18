FROM python:3.14-slim
# Подпись берёт локальное время контейнера; пояс переопределяется через TZ в .env
ENV TZ=Europe/Moscow
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py shelby.gif Roboto-Black.ttf ./
USER nobody
CMD ["python", "main.py"]
