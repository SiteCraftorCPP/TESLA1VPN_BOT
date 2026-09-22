"""Replace 📱 with 5G in Remnawave host remark / serverDescription (subscription list)."""

from __future__ import annotations

import json
import urllib.request

from app.config import settings

PHONE = '\U0001f4f1'


def _swap_phone(text: str) -> str:
    if not text or PHONE not in text:
        return text
    out = text.replace(PHONE + ' ', '5G ').replace(' ' + PHONE, ' 5G').replace(PHONE, '5G')
    return ' '.join(out.split())


def _api(method: str, path: str, body: dict | None = None) -> dict:
    params = settings.get_remnawave_auth_params()
    token = params.get('api_key', '')
    base = (params.get('base_url') or '').rstrip('/')
    data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
    req = urllib.request.Request(
        f'{base}{path}',
        data=data,
        method=method,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=utf-8',
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    params = settings.get_remnawave_auth_params()
    base = (params.get('base_url') or '').rstrip('/')
    hosts = _api('GET', '/api/hosts')['response']
    patched = 0
    for h in hosts:
        remark = h.get('remark') or ''
        desc = h.get('serverDescription') or ''
        new_remark = _swap_phone(remark)
        new_desc = _swap_phone(desc)
        # LTE CDN host: force canonical label
        if 'lte' in (h.get('path') or '').lower() or 'projectweb' in (h.get('address') or ''):
            if PHONE in new_remark or new_remark.strip() in ('🇫🇷', 'LTE', '🇫🇷 LTE'):
                new_remark = '🇫🇷 5G'
            if PHONE in new_desc or new_desc.strip() in ('🇫🇷', 'LTE', '🇫🇷 LTE'):
                new_desc = '🇫🇷 5G'
        if new_remark == remark and new_desc == desc:
            continue
        patch = {
            'uuid': h['uuid'],
            'remark': new_remark,
            'serverDescription': new_desc,
            'address': h.get('address'),
            'port': h.get('port'),
            'path': h.get('path'),
            'sni': h.get('sni'),
            'host': h.get('host'),
            'alpn': h.get('alpn'),
            'fingerprint': h.get('fingerprint'),
            'securityLayer': h.get('securityLayer'),
            'isDisabled': h.get('isDisabled'),
            'isHidden': h.get('isHidden'),
            'nodes': h.get('nodes') or [],
            'inbound': h.get('inbound'),
            'xhttpExtraParams': h.get('xhttpExtraParams'),
        }
        _api('PATCH', '/api/hosts', patch)
        print('patched', h.get('uuid'), remark, '->', new_remark)
        patched += 1
    print('lte_5g_done', patched)


if __name__ == '__main__':
    main()
