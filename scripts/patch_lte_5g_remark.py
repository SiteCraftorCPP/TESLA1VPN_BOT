#!/usr/bin/env python3
"""Replace phone emoji in subscription host names with 5G (Remnawave panel)."""
from __future__ import annotations

import sys

import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PHONE = '\U0001f4f1'  # 📱

REMOTE = r"""
set -e
cd /opt/tesla1vpn && git pull origin main
docker cp /opt/tesla1vpn/bot/app/patch_lte_5g_remark.py remnawave_bot:/app/app/patch_lte_5g_remark.py
SHORT=$(docker exec remnawave_bot_db psql -U remnawave_user -d remnawave_bot -tAc \
  "SELECT remnawave_short_uuid FROM subscriptions WHERE status='active' AND remnawave_short_uuid IS NOT NULL ORDER BY id DESC LIMIT 1" | tr -d '[:space:]')
echo "verify_short=$SHORT"
docker exec -e VERIFY_SUB_SHORT="$SHORT" remnawave_bot python app/patch_lte_5g_remark.py

docker exec remnawave_bot curl -sk "https://projecthub.su/api/sub/${SHORT}" -H "User-Agent: Happ/4.11.0" | docker exec -i remnawave_bot python -c "
import sys, base64, json
raw = sys.stdin.read().strip()
phone = chr(0x1F4F1)
print('body_len', len(raw))
print('body_head', raw[:220])
if not raw or raw[0] in '{[':
    try:
        d = json.loads(raw) if raw else {}
        print('json', d)
    except Exception:
        pass
    raise SystemExit(0)
try:
    t = base64.b64decode(raw).decode('utf-8', 'replace')
except Exception as e:
    print('b64_err', e)
    raise SystemExit(0)
for line in t.splitlines():
    if '#' in line:
        tag = line.split('#')[-1]
        if phone in tag or '5G' in tag or 'lte' in line.lower():
            print('tag', tag)
"

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
