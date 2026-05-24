#!/usr/bin/env python3
"""
Threads長寿命トークンを refresh_access_token API で延長し、
GitHub Secret THREADS_ACCESS_TOKEN を上書きする。

Meta仕様:
  - 24時間以上経過した長寿命トークンしか refresh できない
  - refresh後の新トークンも60日有効
"""
import os
import sys
import base64
import requests
from nacl import encoding, public

current_token = os.environ["THREADS_ACCESS_TOKEN"]
gh_pat        = os.environ["GH_PAT"]
repo          = os.environ["GITHUB_REPOSITORY"]

print("🔄 Threadsトークンを更新中...")
resp = requests.get(
    f"https://graph.threads.net/refresh_access_token"
    f"?grant_type=th_refresh_token&access_token={current_token}",
    timeout=15,
)
data = resp.json()
if "access_token" not in data:
    print(f"❌ 更新失敗: {data}")
    sys.exit(1)

new_token = data["access_token"]
days = data.get("expires_in", 0) // 86400
print(f"✅ 新トークン取得（有効期限：{days}日）")

print("🔐 GitHub Secretを更新中...")
headers = {
    "Authorization": f"token {gh_pat}",
    "Accept": "application/vnd.github.v3+json",
}
key_resp = requests.get(
    f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
    headers=headers, timeout=10,
)
key_data = key_resp.json()

pub_key = public.PublicKey(key_data["key"].encode(), encoding.Base64Encoder())
encrypted = base64.b64encode(public.SealedBox(pub_key).encrypt(new_token.encode())).decode()

update = requests.put(
    f"https://api.github.com/repos/{repo}/actions/secrets/THREADS_ACCESS_TOKEN",
    headers=headers,
    json={"encrypted_value": encrypted, "key_id": key_data["key_id"]},
    timeout=10,
)
if update.status_code in [201, 204]:
    print("✅ GitHub Secret更新完了！")
else:
    print(f"❌ 失敗：{update.status_code} {update.text}")
    sys.exit(1)
