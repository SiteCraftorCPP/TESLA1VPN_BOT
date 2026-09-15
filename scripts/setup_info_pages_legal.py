#!/usr/bin/env python3
"""Create/update Info Pages for privacy/offer (replaces_tab) on production."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
LEGAL_DIR = Path(__file__).resolve().parent / "legal_content"

HOST = "89.22.233.21"
USER = "root"
PASS = "vZTD3R6sSJx7"


def plain_to_html(text: str) -> str:
    """Convert plain legal text to simple HTML for Info Pages."""
    blocks = [b.strip() for b in text.strip().split("\n\n") if b.strip()]
    parts: list[str] = []

    for block in blocks:
        lines = block.split("\n")
        # ALL CAPS short title / section header
        if len(lines) == 1:
            line = lines[0].strip()
            if re.match(r"^\d+\.\s+[А-ЯA-Z]", line) and len(line) < 120:
                parts.append(f"<h2>{line}</h2>")
                continue
            if line.isupper() or (
                len(line) < 80 and "|" in line
            ) or re.match(r"^Редакция от ", line):
                parts.append(f"<h2>{line}</h2>")
                continue

        bullet_lines = [ln for ln in lines if ln.strip().startswith("•")]
        if bullet_lines and len(bullet_lines) == len([ln for ln in lines if ln.strip()]):
            items = "".join(f"<li>{ln.strip()[1:].strip()}</li>" for ln in bullet_lines)
            parts.append(f"<ul>{items}</ul>")
            continue

        if bullet_lines:
            prefix = "<br/>".join(ln for ln in lines if ln.strip() and not ln.strip().startswith("•"))
            items = "".join(
                f"<li>{ln.strip()[1:].strip()}</li>"
                for ln in lines
                if ln.strip().startswith("•")
            )
            html = ""
            if prefix:
                html += f"<p>{prefix}</p>"
            html += f"<ul>{items}</ul>"
            parts.append(html)
            continue

        parts.append(f"<p>{'<br/>'.join(lines)}</p>")

    return "".join(parts)


def plain_to_telegram_html(text: str) -> str:
    """Plain text for privacy_policies / public_offers tables (bot API)."""
    return text.strip()


def load_payload() -> dict:
    privacy_plain = (LEGAL_DIR / "privacy_ru.txt").read_text(encoding="utf-8")
    offer_plain = (LEGAL_DIR / "offer_ru.txt").read_text(encoding="utf-8")

    return {
        "privacy": {
            "slug": "privacy-policy",
            "title": {"ru": "Политика конфиденциальности", "en": "Privacy Policy"},
            "content": {
                "ru": plain_to_html(privacy_plain),
                "en": plain_to_html(privacy_plain),
            },
            "replaces_tab": "privacy",
            "sort_order": 10,
            "plain": privacy_plain,
        },
        "offer": {
            "slug": "public-offer",
            "title": {"ru": "Публичная оферта", "en": "Public Offer"},
            "content": {
                "ru": plain_to_html(offer_plain),
                "en": plain_to_html(offer_plain),
            },
            "replaces_tab": "offer",
            "sort_order": 20,
            "plain": offer_plain,
        },
    }


def main() -> None:
    payload = load_payload()
    payload_json = json.dumps(payload, ensure_ascii=False)

    remote = f"""
import json
import subprocess
import urllib.request

payload = json.loads({payload_json!r})

def psql(q):
    return subprocess.run(
        ["docker", "exec", "remnawave_bot_db", "psql", "-U", "remnawave_user", "-d", "remnawave_bot", "-v", "ON_ERROR_STOP=1", "-c", q],
        capture_output=True,
        text=True,
    )

def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

# FAQ off
psql(
    "INSERT INTO faq_settings (language, is_enabled) VALUES ('ru', false) "
    "ON CONFLICT (language) DO UPDATE SET is_enabled = false, updated_at = NOW();"
)

for key in ("privacy", "offer"):
    page = payload[key]
    plain = page["plain"]
    title_json = json.dumps(page["title"], ensure_ascii=False)
    content_json = json.dumps(page["content"], ensure_ascii=False)
    slug = page["slug"]
    replaces = page["replaces_tab"]
    sort_order = page["sort_order"]

    table = "privacy_policies" if key == "privacy" else "public_offers"
    r = psql(
        f"INSERT INTO {{table}} (language, content, is_enabled) VALUES ('ru', "
        + sql_quote(plain)
        + ", true) ON CONFLICT (language) DO UPDATE SET content = EXCLUDED.content, is_enabled = true, updated_at = NOW();"
    )
    print(table, r.returncode, len(plain))

    psql(
        "UPDATE info_pages SET replaces_tab = NULL, updated_at = NOW() WHERE replaces_tab = "
        + sql_quote(replaces)
        + " AND slug <> "
        + sql_quote(slug)
        + ";"
    )

    q = (
        "INSERT INTO info_pages (slug, title, content, page_type, is_active, sort_order, replaces_tab) VALUES ("
        + sql_quote(slug)
        + ", "
        + sql_quote(title_json)
        + "::jsonb, "
        + sql_quote(content_json)
        + "::jsonb, "
        + "'page', true, "
        + str(sort_order)
        + ", "
        + sql_quote(replaces)
        + ") ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title, content = EXCLUDED.content, "
        "page_type = EXCLUDED.page_type, is_active = true, sort_order = EXCLUDED.sort_order, "
        "replaces_tab = EXCLUDED.replaces_tab, updated_at = NOW();"
    )
    r = psql(q)
    print("info_page", key, r.returncode, len(content_json))
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(1)

for path in [
    "/cabinet/info-pages/tab-replacements",
    "/cabinet/info-pages/privacy-policy",
    "/cabinet/info-pages/public-offer",
]:
    body = urllib.request.urlopen("https://cabinet.projecthub.su" + path, timeout=20).read().decode("utf-8", "replace")
    print(path, "len", len(body))

print("INFO_PAGES_LEGAL_OK")
"""

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30, allow_agent=False, look_for_keys=False)

    # upload legal text files too
    sftp = c.open_sftp()
    for name in ("privacy_ru.txt", "offer_ru.txt"):
        local = LEGAL_DIR / name
        remote_path = f"/opt/tesla1vpn/scripts/legal_content/{name}"
        try:
            sftp.stat("/opt/tesla1vpn/scripts/legal_content")
        except FileNotFoundError:
            sftp.mkdir("/opt/tesla1vpn/scripts/legal_content")
        sftp.put(str(local), remote_path)
    sftp.put(str(Path(__file__).resolve()), "/opt/tesla1vpn/scripts/setup_info_pages_legal.py")
    sftp.close()

    _, o, e = c.exec_command("python3 << 'PY'\n" + remote + "\nPY", timeout=180)
    out = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    c.close()
    print(out)
    if err.strip():
        print("ERR", err[-2000:])
    if "INFO_PAGES_LEGAL_OK" not in out:
        raise SystemExit("setup failed")


if __name__ == "__main__":
    main()
