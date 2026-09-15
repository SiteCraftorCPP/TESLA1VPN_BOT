#!/usr/bin/env python3
"""Create Info Pages for privacy/offer (replaces_tab) and disable FAQ on production."""
from __future__ import annotations

import json
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "89.22.233.21"
USER = "root"
PASS = "vZTD3R6sSJx7"

PRIVACY_RU = (
    "🔒 <b>Политика конфиденциальности</b>\n\n"
    "Мы обязуемся защищать вашу конфиденциальность и личные данные.\n\n"
    "<b>Сбор данных:</b>\n"
    "• Мы собираем только необходимую информацию для предоставления услуг\n"
    "• Данные используются исключительно для работы сервиса\n\n"
    "<b>Защита данных:</b>\n"
    "• Ваши данные защищены современными методами шифрования\n"
    "• Мы не передаем данные третьим лицам без вашего согласия\n\n"
    "<b>Ваши права:</b>\n"
    "• Вы можете запросить информацию о хранимых данных\n"
    "• Вы можете запросить удаление ваших данных\n\n"
    "<b>Используя сервис, вы соглашаетесь с политикой конфиденциальности.</b>"
)

OFFER_RU = (
    "📄 <b>Публичная оферта</b>\n\n"
    "Настоящий документ является официальным предложением (публичной офертой) "
    "сервиса TESLA VPN заключить договор на оказание услуг VPN на изложенных ниже условиях.\n\n"
    "<b>1. Термины</b>\n"
    "• «Исполнитель» — администрация сервиса TESLA VPN\n"
    "• «Пользователь» — физическое лицо, принявшее условия настоящей оферты\n"
    "• «Услуга» — предоставление доступа к VPN-инфраструктуре в рамках оплаченной подписки\n\n"
    "<b>2. Предмет оферты</b>\n"
    "Исполнитель предоставляет Пользователю доступ к VPN-сервису, "
    "а Пользователь оплачивает услуги в соответствии с выбранным тарифом.\n\n"
    "<b>3. Порядок оказания услуг</b>\n"
    "• Доступ предоставляется после оплаты подписки через бота или личный кабинет\n"
    "• Конфигурация подключения выдаётся в виде подписки для VPN-клиентов\n"
    "• Срок действия определяется выбранным периодом оплаты\n\n"
    "<b>4. Стоимость и оплата</b>\n"
    "• Стоимость услуг указана в боте и личном кабинете на момент оплаты\n"
    "• Оплата производится способами, доступными в сервисе\n"
    "• Услуга считается оказанной с момента предоставления доступа\n\n"
    "<b>5. Права и обязанности</b>\n"
    "• Пользователь обязуется не использовать сервис для противоправных действий\n"
    "• Исполнитель обязуется обеспечивать работу сервиса в рамках технических возможностей\n"
    "• Исполнитель вправе приостановить доступ при нарушении правил\n\n"
    "<b>6. Возврат средств</b>\n"
    "Возврат возможен в случаях, предусмотренных законодательством и правилами сервиса, "
    "при обращении в поддержку.\n\n"
    "<b>7. Ответственность</b>\n"
    "Сервис предоставляется «как есть». Исполнитель не несёт ответственности за перебои, "
    "вызванные действиями третьих лиц или ограничениями на стороне Пользователя.\n\n"
    "<b>8. Поддержка</b>\n"
    "По вопросам работы сервиса: @TESLA1VPN_BOT\n\n"
    "<b>Оплачивая подписку, Пользователь подтверждает согласие с условиями настоящей оферты.</b>"
)


def tg_html_to_page_html(text: str) -> str:
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "".join(f"<p>{part.replace(chr(10), '<br/>')}</p>" for part in parts)


PAYLOAD = {
    "privacy": {
        "slug": "privacy-policy",
        "title": {"ru": "Политика конфиденциальности", "en": "Privacy Policy"},
        "content": {"ru": tg_html_to_page_html(PRIVACY_RU), "en": tg_html_to_page_html(PRIVACY_RU)},
        "replaces_tab": "privacy",
        "sort_order": 10,
    },
    "offer": {
        "slug": "public-offer",
        "title": {"ru": "Публичная оферта", "en": "Public Offer"},
        "content": {"ru": tg_html_to_page_html(OFFER_RU), "en": tg_html_to_page_html(OFFER_RU)},
        "replaces_tab": "offer",
        "sort_order": 20,
    },
    "privacy_plain": PRIVACY_RU,
    "offer_plain": OFFER_RU,
}


def main() -> None:
    payload_json = json.dumps(PAYLOAD, ensure_ascii=False)
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

r = psql(
    "INSERT INTO faq_settings (language, is_enabled) VALUES ('ru', false) "
    "ON CONFLICT (language) DO UPDATE SET is_enabled = false, updated_at = NOW();"
)
print("faq_settings:", r.returncode, (r.stdout + r.stderr).strip()[:200])

r = psql(
    "INSERT INTO privacy_policies (language, content, is_enabled) VALUES ('ru', "
    + sql_quote(payload["privacy_plain"])
    + ", true) ON CONFLICT (language) DO UPDATE SET content = EXCLUDED.content, is_enabled = true, updated_at = NOW();"
)
print("privacy_policies:", r.returncode)

r = psql(
    "INSERT INTO public_offers (language, content, is_enabled) VALUES ('ru', "
    + sql_quote(payload["offer_plain"])
    + ", true) ON CONFLICT (language) DO UPDATE SET content = EXCLUDED.content, is_enabled = true, updated_at = NOW();"
)
print("public_offers:", r.returncode)

for key in ("privacy", "offer"):
    page = payload[key]
    title_json = json.dumps(page["title"], ensure_ascii=False)
    content_json = json.dumps(page["content"], ensure_ascii=False)
    slug = page["slug"]
    replaces = page["replaces_tab"]
    sort_order = page["sort_order"]

    psql("UPDATE info_pages SET replaces_tab = NULL, updated_at = NOW() WHERE replaces_tab = "
         + sql_quote(replaces) + " AND slug <> " + sql_quote(slug) + ";")

    q = (
        "INSERT INTO info_pages (slug, title, content, page_type, is_active, sort_order, replaces_tab) VALUES ("
        + sql_quote(slug) + ", "
        + sql_quote(title_json) + "::jsonb, "
        + sql_quote(content_json) + "::jsonb, "
        + "'page', true, " + str(sort_order) + ", " + sql_quote(replaces) + ") "
        "ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title, content = EXCLUDED.content, "
        "page_type = EXCLUDED.page_type, is_active = true, sort_order = EXCLUDED.sort_order, "
        "replaces_tab = EXCLUDED.replaces_tab, updated_at = NOW();"
    )
    r = psql(q)
    print("info_page", key + ":", r.returncode, (r.stdout + r.stderr).strip()[:300])
    if r.returncode != 0:
        raise SystemExit(1)

print("=== verify ===")
for path in [
    "/cabinet/info-pages/tab-replacements",
    "/cabinet/info-pages/privacy-policy",
    "/cabinet/info-pages/public-offer",
]:
    body = urllib.request.urlopen("https://cabinet.projecthub.su" + path, timeout=20).read().decode("utf-8", "replace")
    print(path, "len", len(body), body[:240].replace("\\n", " "))

print("INFO_PAGES_LEGAL_OK")
"""

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30, allow_agent=False, look_for_keys=False)
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
