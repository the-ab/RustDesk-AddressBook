FROM python:3.13.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata openssh-client ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 rab \
    && useradd --uid 10001 --gid rab --home-dir /app --shell /usr/sbin/nologin rab

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement requirements.txt

COPY --chown=rab:rab . .
RUN mkdir -p /data /backups /tmp/rab \
    && chown -R rab:rab /app /data /backups /tmp/rab \
    && chmod +x /app/entrypoint.sh /app/scripts/*.sh

USER 10001:10001

EXPOSE 5000 5443

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "/app/scripts/healthcheck.py"]

CMD ["/app/entrypoint.sh"]
