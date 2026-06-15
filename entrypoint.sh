#!/bin/sh
set -e

echo "Waiting for database at ${DB_HOST:-db}:${DB_PORT:-5432}..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER}" -d "${DB_NAME}" > /dev/null 2>&1; do
  sleep 1
done
echo "Database is up."

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Seeding RBAC roles..."
python manage.py seed_roles

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting: $@"
exec "$@"