#!/usr/bin/env bash
# Restores the database from a backup.sh dump. Stops backend+bot first so
# nothing writes to the DB mid-restore, and asks for explicit confirmation
# since this replaces all current data.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -ne 1 ]; then
  echo "Usage: $0 <backup-file.sql.gz>"
  echo "Get one back from Telegram if it's not already in ./backups/"
  exit 1
fi
FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "File not found: $FILE"
  exit 1
fi

echo "This REPLACES the current database with the contents of: $FILE"
read -r -p "Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Cancelled — nothing changed."
  exit 1
fi

docker compose stop backend bot

docker compose exec -T db psql -U zanjan -d postgres -c "DROP DATABASE IF EXISTS zanjan_campaign;"
docker compose exec -T db psql -U zanjan -d postgres -c "CREATE DATABASE zanjan_campaign;"
gunzip -c "$FILE" | docker compose exec -T db psql -U zanjan zanjan_campaign

docker compose start backend bot
echo "Restore complete — backend and bot are back up."
