#!/usr/bin/env bash
set -e

# Espera a que Postgres este disponible
if [ -n "$POSTGRES_HOST" ]; then
    echo "Esperando a Postgres en $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    until nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
        sleep 0.5
    done
    echo "Postgres disponible."
fi

# Migraciones y archivos estaticos
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

exec "$@"
