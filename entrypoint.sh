#!/bin/sh
set -eu

APP_HTTP_PORT="${APP_HTTP_PORT:-5000}"
APP_HTTPS_PORT="${APP_HTTPS_PORT:-5443}"
APP_WORKERS="${APP_WORKERS:-1}"
APP_THREADS="${APP_THREADS:-4}"
APP_TIMEOUT="${APP_TIMEOUT:-60}"
APP_ENABLE_HTTP="${APP_ENABLE_HTTP:-true}"
APP_ENABLE_HTTPS="${APP_ENABLE_HTTPS:-true}"
HTTPS_CERT_FILE="${HTTPS_CERT_FILE:-/data/certs/addressbook.crt}"
HTTPS_KEY_FILE="${HTTPS_KEY_FILE:-/data/certs/addressbook.key}"

base_args="--workers ${APP_WORKERS} --threads ${APP_THREADS} --timeout ${APP_TIMEOUT} --access-logfile - --error-logfile - wsgi:app"

if [ "${APP_ENABLE_HTTPS}" = "true" ] || [ "${APP_ENABLE_HTTPS}" = "1" ] || [ "${APP_ENABLE_HTTPS}" = "yes" ]; then
  export HTTPS_CERT_FILE HTTPS_KEY_FILE
  python /app/scripts/generate_selfsigned.py
fi

pids=""

if [ "${APP_ENABLE_HTTP}" = "true" ] || [ "${APP_ENABLE_HTTP}" = "1" ] || [ "${APP_ENABLE_HTTP}" = "yes" ]; then
  sh -c "gunicorn --bind 0.0.0.0:${APP_HTTP_PORT} ${base_args}" &
  pids="$pids $!"
fi

if [ "${APP_ENABLE_HTTPS}" = "true" ] || [ "${APP_ENABLE_HTTPS}" = "1" ] || [ "${APP_ENABLE_HTTPS}" = "yes" ]; then
  sh -c "gunicorn --bind 0.0.0.0:${APP_HTTPS_PORT} --certfile '${HTTPS_CERT_FILE}' --keyfile '${HTTPS_KEY_FILE}' ${base_args}" &
  pids="$pids $!"
fi

if [ -z "$pids" ]; then
  echo "APP_ENABLE_HTTP und APP_ENABLE_HTTPS sind beide deaktiviert. Mindestens ein Listener muss aktiv sein." >&2
  exit 1
fi

trap 'kill $pids 2>/dev/null || true; exit 0' INT TERM

while :; do
  for pid in $pids; do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || status=$?
      status="${status:-1}"
      kill $pids 2>/dev/null || true
      wait 2>/dev/null || true
      exit "$status"
    fi
  done
  sleep 2
done
