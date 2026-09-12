#!/usr/bin/env bash
# Restores from a backup.sh full archive (database + uploads + .env files).
# Stops backend+bot first so nothing writes mid-restore. Always restores the
# database and uploads; asks before overwriting current secrets/.env, since
# that's only wanted when rebuilding on a brand-new server (see README.md's
# "از دست رفتن کامل سرور" section) — not for an in-place same-server restore.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -ne 1 ]; then
  echo "Usage: $0 <backup-archive>.tar.gz"
  echo "Get one back from Telegram if it's not already in ./backups/"
  exit 1
fi
FILE="$1"
[ -f "$FILE" ] || { echo "File not found: $FILE"; exit 1; }

echo "این عملیات دیتابیس و فایل‌های آپلودی فعلی رو با محتوای این بکاپ جایگزین می‌کنه: $FILE"
read -r -p "برای ادامه 'yes' رو تایپ کن: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "لغو شد — چیزی تغییر نکرد."
  exit 1
fi

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT
tar xzf "$FILE" -C "$WORK_DIR"

docker compose stop backend bot

if [ -f "$WORK_DIR/database.sql.gz" ]; then
  echo "-- بازیابی دیتابیس..."
  docker compose exec -T db psql -U zanjan -d postgres -c "DROP DATABASE IF EXISTS zanjan_campaign;"
  docker compose exec -T db psql -U zanjan -d postgres -c "CREATE DATABASE zanjan_campaign;"
  gunzip -c "$WORK_DIR/database.sql.gz" | docker compose exec -T db psql -U zanjan zanjan_campaign
else
  echo "هشدار: این بکاپ database.sql.gz نداشت — دیتابیس دست‌نخورده موند." >&2
fi

if [ -f "$WORK_DIR/uploads.tar.gz" ]; then
  echo "-- بازیابی فایل‌های آپلودی (ویس‌ها)..."
  rm -rf backend/uploads
  tar xzf "$WORK_DIR/uploads.tar.gz" -C backend
fi

if [ -f "$WORK_DIR/backend.env" ] || [ -f "$WORK_DIR/root.env" ]; then
  read -r -p "تنظیمات/رمزهای داخل بکاپ (توکن بات، رمز دیتابیس، ...) هم جایگزین تنظیمات فعلی بشه؟ فقط موقع راه‌اندازی روی سرور تازه لازمه. [y/N]: " RESTORE_ENV
  if [ "$RESTORE_ENV" = "y" ] || [ "$RESTORE_ENV" = "Y" ]; then
    [ -f "$WORK_DIR/backend.env" ] && cp "$WORK_DIR/backend.env" backend/.env
    [ -f "$WORK_DIR/root.env" ] && cp "$WORK_DIR/root.env" .env
    echo "تنظیمات بازیابی شد — برای اعمال، سرویس‌ها رو کامل بالا می‌آریم: docker compose up -d"
    docker compose up -d
  fi
fi

docker compose start backend bot
echo "بازیابی کامل شد — بک‌اند و بات دوباره بالان."
