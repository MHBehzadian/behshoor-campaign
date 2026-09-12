#!/usr/bin/env bash
# Full disaster-recovery backup — database + uploaded voice notes + the
# .env files themselves (bot token, DB password, JWT secret) — bundled into
# one archive and sent straight to the admin's Telegram DM via the campaign
# bot. If the server disappears entirely, this one file plus the GitHub repo
# is everything needed to stand the whole thing back up on a new machine —
# see README.md's "از دست رفتن کامل سرور" section.
#
# Runs on a cron (install.sh wires this up every 6 hours). Safe to run by
# hand any time: `./scripts/backup.sh`.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
source backend/.env
[ -f .env ] && source .env
set +a

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="backups"
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$BACKUP_DIR"

echo "-- دیتابیس..."
docker compose exec -T db pg_dump -U zanjan zanjan_campaign | gzip > "$WORK_DIR/database.sql.gz"

if [ -d backend/uploads ] && [ -n "$(ls -A backend/uploads 2>/dev/null)" ]; then
  echo "-- فایل‌های آپلودی (ویس‌ها)..."
  tar czf "$WORK_DIR/uploads.tar.gz" -C backend uploads
fi

# Needed to redeploy with the exact same bot token / DB password / JWT
# secret on a fresh server, instead of generating new ones and losing access.
cp backend/.env "$WORK_DIR/backend.env"
[ -f .env ] && cp .env "$WORK_DIR/root.env"

ARCHIVE="$BACKUP_DIR/behshoor-campaign-full-$TIMESTAMP.tar.gz"
tar czf "$ARCHIVE" -C "$WORK_DIR" .

SIZE_MB=$(du -m "$ARCHIVE" | cut -f1)
if [ "$SIZE_MB" -ge 49 ]; then
  echo "هشدار: بکاپ ${SIZE_MB}MB شده — نزدیک سقف ۵۰ مگابایت بات تلگرامه و ممکنه ارسالش شکست بخوره." >&2
  echo "فایل محلی همچنان اینجاست: $ARCHIVE" >&2
fi

if [ -n "${BACKUP_CHAT_ID:-}" ] && [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  curl -fsS -F document=@"$ARCHIVE" \
    -F chat_id="$BACKUP_CHAT_ID" \
    -F caption="بکاپ کامل کمپین به‌شور (دیتابیس + فایل‌ها + تنظیمات) — ${TIMESTAMP}" \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument" > /dev/null
  echo "Full backup sent to Telegram: $ARCHIVE"
else
  echo "BACKUP_CHAT_ID یا TELEGRAM_BOT_TOKEN توی backend/.env نیست — فقط محلی ذخیره شد: $ARCHIVE"
fi

# Keep the last 30 local copies; Telegram is the real off-site archive.
ls -1t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm --
