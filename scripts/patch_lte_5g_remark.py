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
cd bot && docker compose build bot && docker compose up -d --force-recreate bot
sleep 12
docker exec remnawave_bot python app/patch_lte_5g_remark.py
curl -sk 'https://projecthub.su/api/sub/Cb2j_LH614VtASaJ' -H 'User-Agent: Happ/4.11.0' | python3 -c "import sys,json; d=json.load(sys.stdin); items=d if isinstance(d,list) else [d]; print([c.get('remarks') for c in items if '5G' in (c.get('remarks') or '') or '\U0001f4f1' in (c.get('remarks') or '')][:5])"
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
