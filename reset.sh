#!/usr/bin/env bash
# Чистый пересбор стека monopanel/domains.
# Сносит ЛЮБЫЕ старые контейнеры этого проекта (в т.ч. призраки со старым
# именем monopanel-* и старым портом 8080), затем собирает и поднимает заново
# на порту 43784.
set -euo pipefail

echo "==> Останавливаю compose-проект (если запущен)…"
docker compose down --remove-orphans 2>/dev/null || true

echo "==> Удаляю старые контейнеры по именам monopanel-* / domainchecker-*…"
docker rm -f monopanel-domains-frontend monopanel-domains-backend 2>/dev/null || true
docker ps -aq --filter "name=domainchecker" | xargs -r docker rm -f 2>/dev/null || true

echo "==> Удаляю любые контейнеры, всё ещё публикующие порт 8080…"
docker ps -aq --filter "publish=8080" | xargs -r docker rm -f 2>/dev/null || true

echo "==> Собираю образы заново (без кэша) и поднимаю…"
docker compose build --no-cache
docker compose up -d --force-recreate

echo "==> Текущее состояние:"
docker compose ps

echo
echo "Готово. Панель: http://localhost:43784"
