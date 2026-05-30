#!/usr/bin/env bash
# Monorepo 前端部署：git pull → npm build → Nginx 静态目录
# 用法（ECS 上）:
#   APP_ROOT=/opt/blog/app bash deploy/scripts/deploy-frontend.sh
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/blog/app}"
FRONTEND_DIR="$APP_ROOT/frontend"

# Nginx root 指向的目录（与 deploy/nginx/blog.conf 一致时可设为 $FRONTEND_DIR/dist）
NGINX_WEB_ROOT="${NGINX_WEB_ROOT:-$FRONTEND_DIR/dist}"

cd "$APP_ROOT"
git pull --ff-only origin main

cd "$FRONTEND_DIR"

if [[ ! -f .env.production ]]; then
  cp .env.production.example .env.production
  echo "已生成 .env.production，请确认 VITE_* 后重新运行本脚本"
fi

npm ci
npm run build

if [[ "$NGINX_WEB_ROOT" != "$FRONTEND_DIR/dist" ]]; then
  mkdir -p "$NGINX_WEB_ROOT"
  rsync -av --delete dist/ "$NGINX_WEB_ROOT/"
  echo "已 rsync 到 $NGINX_WEB_ROOT"
else
  echo "构建完成：$FRONTEND_DIR/dist（Nginx root 应指向此目录）"
fi

# 快速校验：新包是否含着陆页签到组件
if grep -q "签到板" dist/assets/*.js 2>/dev/null; then
  echo "OK: dist 含新版着陆页（签到板）"
else
  echo "WARN: dist 里未找到「签到板」，可能仍是旧构建或构建失败"
fi

echo "若页面仍旧，浏览器 Ctrl+F5；并确认 nginx root: $(grep -R '^\s*root ' /etc/nginx/sites-enabled/ 2>/dev/null || true)"
