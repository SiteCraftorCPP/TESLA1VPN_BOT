#!/usr/bin/env python3
"""Replace phone emoji in subscription host names with 5G (Remnawave panel)."""
from __future__ import annotations

import sys

import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PHONE = '\U0001f4f1'  # 📱

REMOTE = r"""
set -e
cd /opt/tesla1vpn && git fetch origin main && git reset --hard origin/main && git log -1 --oneline
docker cp /opt/tesla1vpn/bot/app/patch_lte_5g_remark.py remnawave_bot:/app/app/patch_lte_5g_remark.py
docker exec remnawave_bot python app/patch_lte_5g_remark.py

# shortUuid from panel (authoritative for /api/sub)
SHORT=$(docker exec remnawave_bot python -c "
import json, urllib.request
from app.config import settings
p=settings.get_remnawave_auth_params()
t=p.get('api_key',''); b=(p.get('base_url') or '').rstrip('/')
r=urllib.request.Request(b+'/api/users?size=1', headers={'Authorization':'Bearer '+t})
with urllib.request.urlopen(r,timeout=30) as resp:
    u=json.loads(resp.read().decode())['response']['users'][0]
print(u.get('shortUuid',''))
")
echo "panel_short=$SHORT"

docker exec -e VERIFY_SUB_SHORT="$SHORT" remnawave_bot python app/patch_lte_5g_remark.py

echo LTE_5G_OK
"""

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.22.233.21', username='root', password='vZTD3R6sSJx7', timeout=30, allow_agent=False, look_for_keys=False)
_, o, e = c.exec_command(REMOTE, timeout=600)
out = o.read().decode('utf-8', 'replace')
err = e.read().decode('utf-8', 'replace')
code = o.channel.recv_exit_status()
c.close()
print(out)
if err.strip():
    print('ERR', err[-1500:])
if code != 0 or 'LTE_5G_OK' not in out:
    raise SystemExit(code or 1)
