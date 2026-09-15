#!/usr/bin/env python3
"""Deploy legal links (privacy + offer) in mini app and branding page."""
from __future__ import annotations

import stat
import sys
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"c:\Users\MOD PC COMPANY\Desktop\TESLA1VPN_BOT")
HOST = "89.22.233.21"
USER = "root"
PASS = "vZTD3R6sSJx7"

FILES = [
    (ROOT / "web/src/components/LegalLinks.tsx", "/opt/tesla1vpn/web/src/components/LegalLinks.tsx"),
    (ROOT / "web/src/pages/Info.tsx", "/opt/tesla1vpn/web/src/pages/Info.tsx"),
    (ROOT / "scripts/setup_info_pages_legal.py", "/opt/tesla1vpn/scripts/setup_info_pages_legal.py"),
    (ROOT / "web/src/pages/Login.tsx", "/opt/tesla1vpn/web/src/pages/Login.tsx"),
    (ROOT / "web/src/pages/Profile.tsx", "/opt/tesla1vpn/web/src/pages/Profile.tsx"),
    (ROOT / "web/static/miniapp/profile.html", "/opt/tesla1vpn/web/static/miniapp/profile.html"),
]

REMOTE = r"""
set -e
PROFILE=/opt/tesla1vpn/web/static/miniapp/profile.html
BRANDING=/opt/caddy/branding/index.html
mkdir -p /opt/caddy/branding /opt/tesla1vpn/web/static/miniapp
cp "$PROFILE" "$BRANDING"
echo '=== branding footer ==='
grep -E 'privacy|offer|оферт|конфид' "$BRANDING" || true
echo '=== BUILD WEB ==='
cd /opt/tesla1vpn/web
docker compose build cabinet-frontend
docker compose up -d --force-recreate cabinet-frontend
sleep 12
echo '=== bundle check ==='
docker exec cabinet_frontend sh -c "grep -l 'info?tab=privacy' /usr/share/nginx/html/assets/*.js 2>/dev/null | head -2 || echo NO_PRIVACY_LINK"
docker exec cabinet_frontend sh -c "grep -l 'LegalLinks' /usr/share/nginx/html/assets/*.js 2>/dev/null | head -2 || true"
curl -sk https://cabinet.projecthub.su/miniapp/profile.html | grep -E 'privacy|offer|оферт' || true
curl -sk https://projecthub.su/branding/ | grep -E 'privacy|offer|оферт' || true
echo DONE
"""


def mkdir_p(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = Path(remote_dir).as_posix().strip("/").split("/")
    cur = ""
    for part in parts:
        cur += "/" + part
        try:
            sftp.stat(cur)
        except FileNotFoundError:
            sftp.mkdir(cur)


def main() -> None:
    for local, _ in FILES:
        if not local.exists():
            raise SystemExit(f"missing local file: {local}")

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30, allow_agent=False, look_for_keys=False)
    sftp = c.open_sftp()
    for local, remote in FILES:
        mkdir_p(sftp, str(Path(remote).parent).replace("\\", "/"))
        print("upload", local.relative_to(ROOT), "->", remote)
        sftp.put(str(local), remote)
        sftp.chmod(remote, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    sftp.close()

    print("uploaded, rebuilding...")
    _, o, e = c.exec_command(REMOTE, timeout=900)
    code = o.channel.recv_exit_status()
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace").strip()
    if err:
        print("ERR", err[-3000:])
    c.close()
    if code != 0:
        raise SystemExit(code)


if __name__ == "__main__":
    main()
