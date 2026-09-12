#!/usr/bin/env bash
# One-line installer:
#   curl -fsSL https://raw.githubusercontent.com/MHBehzadian/behshoor-campaign/main/install.sh | bash
#
# Installs Docker if missing, clones the repo, asks a few questions (works
# fine piped through `bash` because prompts read from /dev/tty explicitly),
# brings up the full stack behind Caddy (automatic HTTPS), migrates the
# database, creates the first admin account, and schedules a Telegram backup
# every 6 hours. Safe to re-run — it only asks again for values still unset.
set -euo pipefail

REPO_URL="https://github.com/MHBehzadian/behshoor-campaign.git"
INSTALL_DIR="${INSTALL_DIR:-/opt/behshoor-campaign}"

ask() {
  # ask <prompt> <varname> [default]
  local prompt="$1" varname="$2" default="${3:-}"
  local value
  if [ -n "$default" ]; then
    read -r -p "$prompt [$default]: " value < /dev/tty
    value="${value:-$default}"
  else
    read -r -p "$prompt: " value < /dev/tty
  fi
  printf -v "$varname" '%s' "$value"
}

echo "== نصب کمپین بازاریابی به‌شور =="

if ! command -v docker >/dev/null 2>&1; then
  echo "-- نصب Docker..."
  curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "خطا: پلاگین docker compose پیدا نشد. لطفاً Docker رو آپدیت کن." >&2
  exit 1
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "-- ریپو از قبل هست، به‌روزرسانی..."
  git -C "$INSTALL_DIR" pull
else
  echo "-- کلون کردن ریپو در $INSTALL_DIR ..."
  sudo mkdir -p "$INSTALL_DIR"
  sudo chown "$USER" "$INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

if [ ! -f backend/.env ]; then
  echo
  echo "-- تنظیمات اولیه (فقط بار اول پرسیده می‌شه):"
  ask "دامنه (باید از قبل DNS‌اش به IP همین سرور اشاره کنه)" DOMAIN "campaign.behshoor-olive.ir"
  ask "توکن بات تلگرام (از @BotFather)" BOT_TOKEN
  ask "آیدی عددی تلگرام شما (برای دریافت بکاپ‌ها — از @userinfobot بگیر)" BACKUP_CHAT_ID
  ask "نام کاربری ادمین وب‌سایت" ADMIN_USERNAME "admin"
  ask "رمز عبور ادمین وب‌سایت" ADMIN_PASSWORD "$(openssl rand -hex 8)"
  POSTGRES_PASSWORD="$(openssl rand -hex 16)"
  SECRET_KEY="$(openssl rand -hex 32)"

  cat > .env <<EOF
DOMAIN=${DOMAIN}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
EOF

  cat > backend/.env <<EOF
DATABASE_URL=postgresql+asyncpg://zanjan:${POSTGRES_PASSWORD}@db:5432/zanjan_campaign
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
SECRET_KEY=${SECRET_KEY}
BACKUP_CHAT_ID=${BACKUP_CHAT_ID}
EOF
  chmod 600 .env backend/.env
else
  echo "-- backend/.env از قبل هست؛ تنظیمات قبلی رو نگه می‌داریم."
  # shellcheck disable=SC1091
  source backend/.env
  # shellcheck disable=SC1091
  source .env
  ask "نام کاربری ادمین وب‌سایت" ADMIN_USERNAME "admin"
  ask "رمز عبور ادمین وب‌سایت (خالی = بدون تغییر)" ADMIN_PASSWORD ""
fi

chmod +x scripts/*.sh

echo "-- بالا آوردن سرویس‌ها (اولین بار کمی طول می‌کشه)..."
docker compose up -d --build

echo "-- منتظر آماده شدن دیتابیس..."
until docker compose exec -T db pg_isready -U zanjan >/dev/null 2>&1; do sleep 2; done

echo "-- اجرای مایگریشن‌ها..."
docker compose exec -T backend alembic upgrade head

if [ -n "${ADMIN_PASSWORD:-}" ]; then
  echo "-- ساخت/به‌روزرسانی کاربر ادمین..."
  docker compose exec -T backend python scripts/create_admin.py --username "$ADMIN_USERNAME" --password "$ADMIN_PASSWORD"
fi

CRON_LINE="0 */6 * * * cd $INSTALL_DIR && ./scripts/backup.sh >> $INSTALL_DIR/backup.log 2>&1"
( crontab -l 2>/dev/null | grep -vF "$INSTALL_DIR/scripts/backup.sh" ; echo "$CRON_LINE" ) | crontab -
echo "-- بکاپ خودکار هر ۶ ساعت به تلگرام تنظیم شد."

echo
echo "== تمام شد =="
echo "سایت: https://${DOMAIN}  (گرفتن گواهی SSL ممکنه چند دقیقه طول بکشه)"
if [ -n "${ADMIN_PASSWORD:-}" ]; then
  echo "ورود ادمین: ${ADMIN_USERNAME} / ${ADMIN_PASSWORD}"
fi
echo "بازیابی سریع در صورت مشکل: ./scripts/restore.sh <فایل-بکاپ>"
