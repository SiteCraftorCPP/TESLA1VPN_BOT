"""One-shot: Remnawave subscription settings + hosts branding for «Хамелеон»."""

from __future__ import annotations

import asyncio
import json
import re
import urllib.request

from app.config import settings
from app.database.crud.system_setting import upsert_system_setting
from app.database.database import AsyncSessionLocal

BRAND_RU = 'Хамелеон'
PROFILE_URL = 'https://cabinet.projecthub.su/miniapp/profile.html'


def _api(method: str, path: str, body: dict | None = None) -> dict:
    params = settings.get_remnawave_auth_params()
    token = params.get('api_key', '')
    base = (params.get('base_url') or '').rstrip('/')
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f'{base}{path}',
        data=data,
        method=method,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


async def _db_name() -> None:
    async with AsyncSessionLocal() as db:
        await upsert_system_setting(db, 'CABINET_BRANDING_NAME', BRAND_RU)
        await db.commit()


def main() -> None:
    asyncio.run(_db_name())
    bot_user = (settings.get_bot_username() or '').strip()
    support = f'https://t.me/{bot_user}' if bot_user else 'https://t.me/i_saidru'

    s = _api('GET', '/api/subscription-settings')['response']
    headers = dict(s.get('customResponseHeaders') or {})
    headers['profile-web-page-url'] = PROFILE_URL
    headers['profile-title'] = BRAND_RU
    headers['content-disposition'] = f'attachment; filename="{BRAND_RU}"'
    patch = {
        'uuid': s['uuid'],
        'profileTitle': BRAND_RU,
        'supportLink': support,
        'profileUpdateInterval': s.get('profileUpdateInterval') or 12,
        'serveJsonAtBaseSubscription': s.get('serveJsonAtBaseSubscription'),
        'isProfileWebpageUrlEnabled': True,
        'isShowCustomRemarks': s.get('isShowCustomRemarks'),
        'customRemarks': s.get('customRemarks'),
        'happAnnounce': f'Добро пожаловать в {BRAND_RU}',
        'happRouting': s.get('happRouting'),
        'customResponseHeaders': headers,
        'randomizeHosts': s.get('randomizeHosts'),
        'responseRules': s.get('responseRules'),
        'hwidSettings': s.get('hwidSettings'),
    }
    _api('PATCH', '/api/subscription-settings', patch)
    print('subscription_settings_ok', BRAND_RU)

    hosts = _api('GET', '/api/hosts')['response']
    fixed = 0
    for h in hosts:
        desc = h.get('serverDescription') or ''
        if 'TESLA' not in desc.upper():
            continue
        new_desc = re.sub(r'TESLA\s*VPN?', BRAND_RU, desc, flags=re.I).strip()
        if new_desc == desc:
            continue
        body = {k: h.get(k) for k in h if k not in ('createdAt', 'updatedAt')}
        body['serverDescription'] = new_desc
        try:
            _api('PATCH', '/api/hosts', body)
            fixed += 1
        except Exception as exc:  # pragma: no cover - panel schema varies per host
            print('host_patch_skip', h.get('uuid'), exc)
    print('hosts_patched', fixed)


if __name__ == '__main__':
    main()
