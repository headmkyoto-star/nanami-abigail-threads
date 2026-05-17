import os
import anthropic
import requests
import random
import time

ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
USER_ID = os.environ.get("THREADS_USER_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/headmkyoto-star/nanami-abigail-threads/main/"
GITHUB_API_BASE = "https://api.github.com/repos/headmkyoto-star/nanami-abigail-threads/contents/"


def list_media(folder, exts):
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        r = requests.get(GITHUB_API_BASE + folder, headers=headers, timeout=15)
        print(f"  list_media({folder!r}) status={r.status_code}")
        if r.status_code != 200:
            return []
        files = r.json()
        if not isinstance(files, list):
            return []
        names = [
            f["name"]
            for f in files
            if f.get("name", "").lower().endswith(exts)
        ]
        print(f"  {folder!r} 内: {len(names)} 件のメディア")
        return names
    except Exception as e:
        print(f"  list_media error: {e}")
        return []


def pick_media():
    """動画9割、画像1割でメディアを選ぶ。無ければテキスト投稿"""
    videos = list_media("videos", (".mp4",))
    images = list_media("images", (".jpg", ".jpeg", ".png", ".webp"))

    # 動画9割 / 画像1割
    if videos and (random.random() < 0.9 or not images):
        name = random.choice(videos)
        return ("VIDEO", GITHUB_RAW_BASE + "videos/" + name.replace(" ", "_"))
    if images:
        name = random.choice(images)
        return ("IMAGE", GITHUB_RAW_BASE + "images/" + name.replace(" ", "_"))
    return (None, None)


def generate_post():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    if random.random() < 0.2:
        prompt = (
            "ドライヘッドスパ専門サロン(ヘッドミント京都祇園店)のセラピスト"
            "「ななみアビゲイル」として、営業系のThreads投稿文を作成してください。"
            "・40〜55文字程度・絵文字基本1つ(1箇所は連続絵文字OK)・改行あり"
            "・ハッシュタグなし・口語表現で自然な文章・余韻あり"
            "・70分3,980円のメニューに触れてもOK"
            "投稿本文のみ出力。"
        )
    else:
        prompt = (
            "ドライヘッドスパ専門サロンのセラピスト「ななみアビゲイル」として、"
            "日常日記系のThreads投稿文を作成してください。"
            "・40〜55文字程度・絵文字基本1つ(1箇所は連続絵文字OK)・改行あり"
            "・ハッシュタグなし・口語表現で自然な文章・余韻あり"
            "・営業色なし、その日の気持ち・施術中のエピソードなど"
            "投稿本文のみ出力。"
        )
    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def post_to_threads(text, media_type, media_url):
    """Threadsへ投稿。media_type: 'IMAGE' / 'VIDEO' / None"""
    base = f"https://graph.threads.net/v1.0/{USER_ID}/threads"
    if media_type == "VIDEO" and media_url:
        params = {
            "media_type": "VIDEO",
            "video_url": media_url,
            "text": text,
            "access_token": ACCESS_TOKEN,
        }
    elif media_type == "IMAGE" and media_url:
        params = {
            "media_type": "IMAGE",
            "image_url": media_url,
            "text": text,
            "access_token": ACCESS_TOKEN,
        }
    else:
        params = {
            "media_type": "TEXT",
            "text": text,
            "access_token": ACCESS_TOKEN,
        }

    r = requests.post(base, params=params, timeout=30)
    print(f"📦 コンテナ作成 status={r.status_code}")
    if r.status_code != 200:
        print(f"❌ {r.text}")
        # 動画失敗ならテキストで再試行
        if media_type == "VIDEO":
            print("↺ 動画失敗、テキストで再試行")
            return post_to_threads(text, None, None)
        return r
    cid = r.json().get("id")
    print(f"   container_id: {cid}")

    # 動画は処理時間が長いのでstatus確認しながら待つ
    wait = 60 if media_type == "VIDEO" else 5
    print(f"⏰ {wait}秒待機(媒体処理待ち)...")
    time.sleep(wait)

    publish_url = f"https://graph.threads.net/v1.0/{USER_ID}/threads_publish"
    pr = requests.post(
        publish_url,
        params={"creation_id": cid, "access_token": ACCESS_TOKEN},
        timeout=30,
    )
    print(f"📤 publish status={pr.status_code}")
    if pr.status_code != 200:
        print(f"❌ publish失敗: {pr.text}")
    return pr


text = generate_post()
print(f"📝 投稿文 ({len(text)}文字):\n{text}\n")

media_type, media_url = pick_media()
if media_type:
    print(f"🎬 メディア種別: {media_type}")
    print(f"   URL: {media_url}\n")
else:
    print("📄 メディアなし(テキスト投稿)\n")

r = post_to_threads(text, media_type, media_url)
if r and r.status_code == 200:
    print("✅ SUCCESS")
else:
    print("❌ FAILED")
