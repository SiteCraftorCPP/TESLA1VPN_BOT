#!/usr/bin/env python3
"""Deploy «Хамелеон» rebrand to production VPS."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
HOST = '89.22.233.21'
USER = 'root'
PASS = 'vZTD3R6sSJx7'

REMOTE = r'''
set -e
cd /opt/tesla1vpn && git fetch origin main && git reset --hard origin/main && git log -1 --oneline

ENV=/opt/tesla1vpn/bot/.env
WEB_ENV=/opt/tesla1vpn/web/.env
set_kv() {
  local file="$1" key="$2" val="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$file"
  else
    echo "${key}=${val}" >> "$file"
  fi
}

set_kv "$ENV" MINIAPP_SERVICE_NAME_RU "Хамелеон"
set_kv "$ENV" MINIAPP_SERVICE_NAME_EN "Chameleon"
set_kv "$ENV" PAYMENT_SERVICE_NAME "Хамелеон"
set_kv "$ENV" SMTP_FROM_NAME "Хамелеон"
set_kv "$WEB_ENV" VITE_APP_NAME "Хамелеон"
set_kv "$WEB_ENV" VITE_APP_LOGO "Х"

cd /opt/tesla1vpn/bot && docker compose build bot && docker compose up -d --force-recreate bot
sleep 12

docker exec remnawave_bot python - <<'PY'
import asyncio
import json
import os
import re
import urllib.request

from app.database.crud.system_setting import set_setting_value
from app.database.database import AsyncSessionLocal

BRAND_RU = "Хамелеон"


async def db_branding() -> None:
    async with AsyncSessionLocal() as db:
        await set_setting_value(db, "CABINET_BRANDING_NAME", BRAND_RU)
        await db.commit()
    print("db_branding_ok", BRAND_RU)


asyncio.run(db_branding())

env = open("/opt/tesla1vpn/bot/.env", encoding="utf-8").read()
token = re.search(r"^REMNAWAVE_API_KEY=(.+)$", env, re.M).group(1).strip()
bot_user = re.search(r"^BOT_USERNAME=(.+)$", env, re.M)
bot_user = bot_user.group(1).strip() if bot_user else ""
support = "https://t.me/" + bot_user if bot_user else "https://t.me/i_saidru"
profile_url = "https://cabinet.projecthub.su/miniapp/profile.html"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        "https://projecthub.su" + path,
        data=data,
        method=method,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


s = api("GET", "/api/subscription-settings")["response"]
headers = dict(s.get("customResponseHeaders") or {})
headers["profile-web-page-url"] = profile_url
headers["profile-title"] = BRAND_RU
headers["content-disposition"] = f'attachment; filename="{BRAND_RU}"'
patch = {
    "uuid": s["uuid"],
    "profileTitle": BRAND_RU,
    "supportLink": support,
    "profileUpdateInterval": s.get("profileUpdateInterval") or 12,
    "serveJsonAtBaseSubscription": s.get("serveJsonAtBaseSubscription"),
    "isProfileWebpageUrlEnabled": True,
    "isShowCustomRemarks": s.get("isShowCustomRemarks"),
    "customRemarks": s.get("customRemarks"),
    "happAnnounce": f"Добро пожаловать в {BRAND_RU}",
    "happRouting": s.get("happRouting"),
    "customResponseHeaders": headers,
    "randomizeHosts": s.get("randomizeHosts"),
    "responseRules": s.get("responseRules"),
    "hwidSettings": s.get("hwidSettings"),
}
api("PATCH", "/api/subscription-settings", patch)
print("subscription_settings_ok", BRAND_RU)

hosts = api("GET", "/api/hosts")["response"]
fixed = 0
for h in hosts:
    desc = h.get("serverDescription") or ""
    if "TESLA" in desc.upper():
        new_desc = re.sub(r"TESLA\s*VPN?", BRAND_RU, desc, flags=re.I).strip()
        if new_desc != desc:
            body = {k: h.get(k) for k in h if k not in ("createdAt", "updatedAt")}
            body["serverDescription"] = new_desc
            api("PATCH", "/api/hosts", body)
            fixed += 1
print("hosts_patched", fixed)
PY

python3 /opt/tesla1vpn/scripts/setup_info_pages_legal.py

cd /opt/tesla1vpn/web && docker compose build cabinet-frontend && docker compose up -d --force-recreate cabinet-frontend

mkdir -p /opt/caddy/branding
cat > /opt/caddy/branding/index.html <<'HTML'
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Хамелеон</title>
<link rel="icon" href="/branding/logo.png"></head><body>Хамелеон</body></html>
HTML

curl -sk "https://projecthub.su/api/sub/Cb2j_LH614VtASaJ" -H "User-Agent: Happ/4.11.0" -D - -o /dev/null | grep -iE 'profile-title|content-disposition' | head -3 || true
echo REBRAND_OK
'''


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30, allow_agent=False, look_for_keys=False)
    _, o, e = c.exec_command(REMOTE, timeout=1200)
    out = o.read().decode('utf-8', 'replace')
    err = e.read().decode('utf-8', 'replace')
    code = o.channel.recv_exit_status()
    c.close()
    print(out[-12000:])
    if err.strip():
        print('ERR', err[-3000:])
    if code != 0 or 'REBRAND_OK' not in out:
        raise SystemExit(code or 1)


if __name__ == '__main__':
    # legal script must exist on server after git pull
    main()
