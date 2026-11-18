FROM python:3.14-slim
# TZ — пояс для тех, кто не настроил свой; переопределяется в .env
ENV TZ=Europe/Moscow DB_PATH=/data/zones.db
RUN mkdir /data && chown nobody /data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py shelby.gif Roboto-Black.ttf ./
USER nobody
CMD ["python", "main.py"]
