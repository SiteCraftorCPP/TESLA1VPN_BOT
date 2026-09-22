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

docker exec remnawave_bot python app/patch_rebrand_panel.py

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
    main()
    legal = ROOT / 'scripts' / 'setup_info_pages_legal.py'
    subprocess.run([sys.executable, str(legal)], check=True)
