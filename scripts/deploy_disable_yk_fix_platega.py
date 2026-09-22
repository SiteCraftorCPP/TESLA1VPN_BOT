#!/usr/bin/env python3
"""Disable YooKassa; ensure Platega label in mini-app."""
import re
import socket

import paramiko

ENV_PATH = "/opt/tesla1vpn/bot/.env"
REPO = "/opt/tesla1vpn"
HEX_LABEL = "d09ad0b0d180d182d0b020d0b820d0a1d091d09f"
PLATEGA_LINE = ("PLATEGA_DISPLAY_NAME=" + bytes.fromhex(HEX_LABEL).decode("utf-8") + "\n").encode(
    "utf-8"
)


def patch_env(raw: bytes) -> bytes:
    raw = re.sub(br"(?m)^YOOKASSA_ENABLED=.*\n?", b"", raw)
    raw = re.sub(br"(?m)^YOOKASSA_SBP_ENABLED=.*\n?", b"", raw)
    raw = re.sub(br"(?m)^PLATEGA_DISPLAY_NAME=.*\n?", b"", raw)
    if b"PLATEGA_ENABLED=true" not in raw:
        raw = raw.rstrip(b"\n") + b"\nPLATEGA_ENABLED=true\n"
    raw = raw.rstrip(b"\n") + b"\nYOOKASSA_ENABLED=false\n" + PLATEGA_LINE
    return raw


def main():
    s = socket.create_connection(("89.22.233.21", 22), timeout=25)
    t = paramiko.Transport(s)
    t.connect(username="root", password="vZTD3R6sSJx7")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c._transport = t

    sftp = c.open_sftp()
    with sftp.file(ENV_PATH, "rb") as f:
        new_env = patch_env(f.read())
    with sftp.file(ENV_PATH, "wb") as f:
        f.write(new_env)
    sftp.close()

    sql = f"""
UPDATE payment_method_configs SET is_enabled = false WHERE method_id IN ('yookassa', 'yookassa_sbp');
UPDATE payment_method_configs SET is_enabled = true, display_name = convert_from(decode('{HEX_LABEL}', 'hex'), 'UTF8') WHERE method_id = 'platega';
"""
    remote = f"""
U=$(grep '^POSTGRES_USER=' {ENV_PATH} | cut -d= -f2)
D=$(grep '^POSTGRES_DB=' {ENV_PATH} | cut -d= -f2)
docker exec -e PGCLIENTENCODING=UTF8 remnawave_bot_db psql -U "$U" -d "$D" -c "{sql.replace(chr(10), ' ')}"
cd {REPO} && git fetch origin main && git reset --hard origin/main
cd {REPO}/web && docker compose build cabinet-frontend && docker compose up -d --force-recreate cabinet-frontend
cd {REPO}/bot && docker compose up -d --force-recreate --no-deps bot
sleep 12
docker exec remnawave_bot python3 -c "from app.config import settings; print('yk', settings.is_yookassa_enabled()); print('pl', settings.get_platega_display_name())"
docker exec -e PGCLIENTENCODING=UTF8 remnawave_bot_db psql -U "$U" -d "$D" -c "SELECT method_id, is_enabled, display_name FROM payment_method_configs WHERE method_id IN ('yookassa','platega');"
curl -sk https://cabinet.projecthub.su/ | grep -o 'ru-[A-Za-z0-9_-]*\\.js' | head -1
echo DONE
"""
    _, o, e = c.exec_command(remote, timeout=600)
    out = o.read().decode("utf-8", "replace")
    print(out.encode("ascii", "replace").decode("ascii"))
    err = e.read().decode("utf-8", "replace").strip()
    if err:
        print("ERR", err[-2500:].encode("ascii", "replace").decode(