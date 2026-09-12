#!/usr/bin/env bash
# Dumps the Postgres DB and sends it straight to the admin's Telegram DM via
# the campaign bot. Meant to run on a cron (install.sh wires this up every 6
# hours) so a bad deploy or a fat-fingered admin action is always one
# `scripts/restore.sh` away from being undone.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
source backend/.env
set +a

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/zanjan-campaign-$TIMESTAMP.sql.gz"

docker compose exec -T db pg_dump -U zanjan zanjan_campaign | gzip > "$FILE"

if [ -n "${BACKUP_CHAT_ID:-}" ] && [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  curl -fsS -F document=@"$FILE" \
    -F chat_id="$BACKUP_CHAT_ID" \
    -F caption="بکاپ دیتابیس کمپین به‌شور — ${TIMESTAMP}" \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument" > /dev/null
  echo "Backup sent to Telegram: $FILE"
else
  echo "BACKUP_CHAT_ID or TELEGRAM_BOT_TOKEN missing in backend/.env — saved locally only: $FILE"
fi

# Keep the last 30 local copies; Telegram is the real off-site archive.
ls -1t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm --
