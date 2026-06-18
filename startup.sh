#!/usr/bin/env bash
# startup.sh — run before gunicorn on Render
set -e

# On cloud platforms, copy the seeded DB to /tmp if not already there
if [ -n "$RENDER" ] || [ -n "$RAILWAY_ENVIRONMENT" ]; then
    mkdir -p /tmp/uploads

    if [ ! -f /tmp/smarthire.db ]; then
        echo "Copying seeded database to /tmp..."
        cp smarthire.db /tmp/smarthire.db
    fi
fi

exec gunicorn app:app
