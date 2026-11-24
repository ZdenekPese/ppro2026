#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS_ON_START:-true}" = "true" ]; then
    echo "[entrypoint] Aplikuji databázové migrace (alembic upgrade head)..."
    alembic upgrade head
fi

if [ "${RUN_SEED_ON_START:-true}" = "true" ]; then
    echo "[entrypoint] Ověřuji a doplňuji výchozí syntetická data (seed)..."
    python -m app.infrastructure.db.seed
fi

echo "[entrypoint] Spouštím příkaz: $*"
exec "$@"
