#!/usr/bin/env python3
"""Enable Platega in mini-app payment list and set user-facing label."""
import socket
from datetime import datetime, timezone

import paramiko

HOST = ("89.22.233.21", "vZTD3R6sSJx7")
ENV_PATH = "/opt/tesla1vpn/bot/.env"
REPO = "/opt/tesla1vpn"
DISPLAY_NAME = "Карта и СБП"

REMOTE_AFTER = rf"""
U=$(grep '^POSTGRES_USER=' {ENV_PATH} | cut -d= -f2)
D=$(grep '^POSTGRES_DB=' {ENV_PATH} | cut -d= -f2)
docker exec remnawave_bot_db psql -U "$U" -d "$D" -c \
"UPDATE payment_method_configs SET is_enabled=true, display_name='{DISPLAY_NAME}' WHERE method_id='platega';"
docker exec remnawave_bot_db psql -U "$U" -d "$D" -c \
"SELECT method_id, display_name, is_enabled FROM payment_method_configs WHERE method_id='platega';"
cd {REPO} && git fetch origin main && git reset --hard origin/main
cd {REPO}/web && docker compose build cabinet-frontend && docker compose up -d --force-recreate cabinet-frontend
cd {REPO}/bot && docker compose up -d --force-recreate --no-deps bot
docker exec remnawave_bot python3 -c "from app.config import settings; print('platega_label', settings.get_platega_display_name())"
echo DONE
"""


def patch_env(content: str) -> str:
    lines = content.splitlines()
    out = []
    seen = False
    for line in lines:
        if line.startswith("PLATEGA_DISPLAY_NAME="):
            if not seen:
                out.append(f"PLATEGA_DISPLAY_NAME={DISPLAY_NAME}")
                seen = True
            continue
        out.append(line)
    if not seen:
        out.append(f"PLATEGA_DISPLAY_NAME={DISPLAY_NAME}")
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    return text


def main():
    s = socket.create_connection((HOST[0], 22), timeout=25)
    t = paramiko.Transport(s)
    t.connect(username="root", password=HOST[1])
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c._transport = t

    sftp = c.open_sftp()
    with sftp.file(ENV_PATH, "r") as f:
        original = f.read().decode("utf-8", errors="replace")
    backup = f"{ENV_PATH}.bak.platega_label.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    with sftp.file(backup, "w") as f:
        f.write(original)
    with sftp.file(ENV_PATH, "w") as f:
        f.write(patch_env(original))
    sftp.close()
    print("env backup", backup)

    _, o, e = c.exec_command(REMOTE_AFTER, timeout=600)
    out = o.read().decode("utf-8", "replace")
    print(out.encode("ascii", "replace").decode("ascii"))
    err = e.read().decode("utf-8", "replace").strip()
    if err:
        print("ERR", err[-2000:].encode("ascii", "replace").decode("ascii"))
    c.close()


if __name__ == "__main__":
    main()
