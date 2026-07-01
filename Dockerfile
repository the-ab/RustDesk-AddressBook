FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /data /backups

EXPOSE 5000 5443

RUN chmod +x /app/entrypoint.sh /app/scripts/*.sh 2>/dev/null || chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
