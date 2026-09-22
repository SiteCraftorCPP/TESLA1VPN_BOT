#!/usr/bin/env python3
"""Sync branding page text 1:1 with profile.html + rename LTE host to phone emoji."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"c:\Users\MOD PC COMPANY\Desktop\TESLA1VPN_BOT")
PROFILE_HTML = (ROOT / "web/static/miniapp/profile.html").read_text(encoding="utf-8")
LTE_HOST_UUID = "4af64504-d67d-4ec5-b8eb-1d5d2314eeef"
LTE_REMARK = "🇫🇷 5G"
LTE_SERVER_DESCRIPTION = "🇫🇷 5G"

REMOTE = rf'''
import json
import os
import subprocess
import urllib.request

PROFILE_HTML = {PROFILE_HTML!r}
LTE_HOST_UUID = "{LTE_HOST_UUID}"
LTE_REMARK = {LTE_REMARK!r}
LTE_SERVER_DESCRIPTION = {LTE_SERVER_DESCRIPTION!r}

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr.strip():
        print("ERR:", r.stderr[-400:])

# 1) Branding page on projecthub.su — same HTML as profile.html
branding_dir = "/opt/caddy/branding"
os.makedirs(branding_dir, exist_ok=True)
open(f"{{branding_dir}}/index.html", "w", encoding="utf-8").write(PROFILE_HTML)
sh("docker cp remnawave_bot:/app/data/branding/logo.png /opt/caddy/branding/logo.png")
sh("curl -sk https://projecthub.su/branding/ | head -20")

# 2) Cabinet profile.html mirror
os.makedirs("/opt/tesla1vpn/web/static/miniapp", exist_ok=True)
open("/opt/tesla1vpn/web/static/miniapp/profile.html", "w", encoding="utf-8").write(PROFILE_HTML)
sh("cd /opt/tesla1vpn/web && docker compose up -d --force-recreate cabinet-frontend 2>&1 | tail -5")
sh("curl -sk https://cabinet.projecthub.su/miniapp/profile.html | head -20")

TOKEN = open("/opt/tesla1vpn/bot/.env").read().split("REMNAWAVE_API_KEY=")[1].split("\\n")[0].strip()
BASE = "https://projecthub.su"

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={{"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

# 3) LTE host -> phone emoji in subscription
hosts = api("GET", "/api/hosts")["response"]
lte = next((h for h in hosts if h.get("uuid") == LTE_HOST_UUID or "LTE" in (h.get("remark") or "")), None)
if lte:
    patch = dict(lte)
    patch["remark"] = LTE_REMARK
    patch["serverDescription"] = LTE_SERVER_DESCRIPTION
    res = api("PATCH", "/api/hosts", patch)
    h = res.get("response") or res
    print("LTE host patched:", h.get("remark"), h.get("serverDescription"))
else:
    print("WARN: LTE host not found")

# 4) Verify subscription remarks
SHORT = "Cb2j_LH614VtASaJ"
req = urllib.request.Request(
    BASE + "/api/sub/" + SHORT,
    headers={{"User-Agent": "Happ/4.11.0 (iOS)"}},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode())
    items = data if isinstance(data, list) else [data]
    print("sub remarks:", [c.get("remarks") for c in items])

print("SITE_LTE_OK")
'''

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("89.22.233.21", username="root", password="vZTD3R6sSJx7", timeout=30)
_, o, e = c.exec_command("python3 << 'PY'\n" + REMOTE + "\nPY", timeout=300)
out = o.read().decode("utf-8", "replace")
err = e.read().decode("utf-8", "replace")
c.close()

out_path = ROOT / "scripts" / "_apply_site_lte_out.txt"
out_path.write_text(out + ("\nERR:\n" + err if err else ""), encoding="utf-8")
print(out.encode("ascii", "replace").decode("ascii"))
if err:
    print("STDERR", err[-500:])
