#!/bin/bash

# Proxy to run `manage.py` (django-admin) commands inside the web container.
#
# Prefers `docker compose exec` against an already-running web container so
# every invocation doesn't pay the cost of spinning up a fresh ephemeral
# container (~150 MB on a heavy Django image). Falls back to `compose run
# --rm` only when web isn't running.

set -e

# Confirmation: only when targeting a non-local DB AND we have a TTY.
# Reads POSTGRES_HOST from .env directly instead of spawning a container
# just to inspect env, which the old script did.
if [ -t 0 ] && [ -f .env ]; then
  DB_HOST=$(grep -E '^POSTGRES_HOST=' .env | cut -d '=' -f2 | tr -d '[:space:]')
  case "$DB_HOST" in
    ''|db|0.0.0.0|localhost) ;;
    *)
      echo "You are running this command against the database at ${DB_HOST}!"
      read -r -p "Are you sure you want to continue? [y/N] " response
      [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]] || exit 1
      ;;
  esac
fi

# `-T` disables TTY allocation, required when invoked from cron / CI / SSH
# action where stdin isn't a TTY.
EXEC_FLAGS=""
[ ! -t 0 ] && EXEC_FLAGS="-T"

if docker compose ps -q web 2>/dev/null | grep -q .; then
  exec docker compose exec $EXEC_FLAGS -w /code/app web /code/app/manage.py "$@"
else
  exec docker compose run --rm $EXEC_FLAGS -w /code/app web /code/app/manage.py "$@"
fi
