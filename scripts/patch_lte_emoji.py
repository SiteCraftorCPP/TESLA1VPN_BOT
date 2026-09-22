#!/usr/bin/env python3
"""Rename LTE -> phone emoji in remark, keep country flag in serverDescription."""
from __future__ import annotations

import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST_UUID = "4af64504-d67d-4ec5-b8eb-1d5d2314eeef"
NEW_REMARK = "\U0001f1eb\U0001f1f7 5G"  # 🇫🇷 5G
NEW_SERVER_DESCRIPTION = "\U0001f1eb\U0001f1f7 5G"

REMOTE = f'''
import json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN=open("/opt/tesla1vpn/bot/.env").read().split("REMNAWAVE_API_KEY=")[1].split("\\n")[0].strip()
BASE="https://projecthub.su"
HOST_UUID="{HOST_UUID}"
NEW_REMARK={NEW_REMARK!r}
NEW_SERVER_DESCRIPTION={NEW_SERVER_DESCRIPTION!r}

def api(method, path, body=None):
    data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req=urllib.request.Request(
        BASE+path,
        data=data,
        method=method,
        headers={{"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json; charset=utf-8"}},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

hosts=api("GET","/api/hosts")["response"]
lte=next(h for h in hosts if h.get("uuid")==HOST_UUID)
patch={{
    "uuid": lte["uuid"],
    "remark": NEW_REMARK,
    "serverDescription": NEW_SERVER_DESCRIPTION,
    "address": lte.get("address"),
    "port": lte.get("port"),
    "path": lte.get("path"),
    "sni": lte.get("sni"),
    "host": lte.get("host"),
    "alpn": lte.get("alpn"),
    "fingerprint": lte.get("fingerprint"),
    "securityLayer": lte.get("securityLayer"),
    "isDisabled": lte.get("isDisabled"),
    "isHidden": lte.get("isHidden"),
    "nodes": lte.get("nodes") or [],
    "inbound": lte.get("inbound"),
    "xhttpExtraParams": lte.get("xhttpExtraParams"),
}}
res=api("PATCH","/api/hosts",patch)
h=res.get("response") or res
print("patched remark:", h.get("remark"))
print("patched serverDescription:", h.get("serverDescription"))

SHORT="Cb2j_LH614VtASaJ"
req=urllib.request.Request(BASE+"/api/sub/"+SHORT, headers={{"User-Agent":"Happ/4.11.0 (iOS)"}})
with urllib.request.urlopen(req, timeout=30) as resp:
    data=json.loads(resp.read().decode("utf-8"))
    items=data if isinstance(data,list) else [data]
    print("sub remarks:", [c.get("remarks") for c in items])
print("LTE_EMOJI_OK")
'''

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("89.22.233.21", username="root", password="vZTD3R6sSJx7", timeout=30)
_, o, e = c.exec_command("python3 << 'PY'\n" + REMOTE + "\nPY", timeout=120)
out = o.read().decode("utf-8", "replace")
err = e.read().decode("utf-8", "replace")
c.close()
print(out.encode("ascii", "backslashreplace").decode("ascii"))
if err:
    print("ERR", err[-800:])
