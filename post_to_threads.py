import anthropic, requests, os, random, time

ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
USER_ID = os.environ.get("THREADS_USER_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/headmkyoto-star/nanami-abigail-threads/main/"
GITHUB_API_BASE = "https://api.github.com/repos/headmkyoto-star/nanami-abigail-threads/contents/"

OPENING_PHRASES = [
    "関西の人で",
    "📍祇園四条駅から徒歩5分",
    "祇園四条駅のすぐ近くで",
    "京都祇園で",
    "京都の人で",
]

MENUS = [
    "ドライヘッドスパ 70分 3,980円",
    "アロママッサージ",
    "小顔矯正コルギ",
]

def get_media():
    """動画のみ選択（画像は使わない）"""
    videos = []
    try:
        r = requests.get(GITHUB_API_BASE + "videos")
        if r.status_code == 200:
            files = r.json()
            if isinstance(files, list):
                for f in files:
                    name = f["name"].lower()
                    if name.endswith((".mp4", ".mov")):
                        url = GITHUB_RAW_BASE + "videos/" + f["name"].replace(" ", "_")
                        videos.append((url, "VIDEO"))
    except: pass

    if videos:
        return random.choice(videos)
    return None, None

def generate_post():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    opening = random.choice(OPENING_PHRASES)
    menu = random.choice(MENUS)

    prompt = f"""京都祇園のリラクゼーションサロン「ななみアビゲイル」の若い女性セラピストとして、Threadsの短い営業投稿を作成してください。

【絶対ルール】
- 投稿は **必ず以下の冒頭フレーズで始める**: 「{opening}」
- メニューは「{menu}」を訴求する
- 文字数は40〜70文字
- 句読点（。、）は使わず、絵文字や改行で区切る
- ハッシュタグは絶対なし
- 改行は1〜2回程度
- 絵文字は以下から3〜5個だけ使う: ✋ 😴 🫧 🙋‍♀️ 🪽 🐑 💤 👀 🥰 🤩 ❓ ✨ 🔥 💆
- 若い女性セラピストの口調（〜ですー、〜ませんか、〜してくださーい等）

【冒頭フレーズの位置】
冒頭フレーズ「{opening}」は必ず投稿の最初に配置すること。例：
- 「関西の人で」+ 「ヘッドスパ受けたい人いませんかー？🙋‍♀️」のように繋げる
- 「📍祇園四条駅から徒歩5分」+ 「70分3,980円で癒します🥰」のように繋げる
- 「京都祇園で」+ 「寝落ちしませんか🐑💤」のように繋げる

【参考にする過去の実投稿（冒頭フレーズを付けたバージョン）】
- 関西の人でオイルマッサージ受けたい人✋私の手で癒させてくださーい😴🫧
- 📍祇園四条駅から徒歩5分 70分3980円でヘッドスパ受けたい人いますかー？🙋‍♀️ 私が全力で施術させていただきます🪽
- 京都祇園で寝落ち率95%のヘッドスパ受けたい人いませんか🤩❓
- 京都の人で 70分3,980円ぽっきりでスッキリしませんか🥰
- 祇園四条駅のすぐ近くでドライヘッドスパ¥3,980で受けたい人🙋‍♀️私の手で癒させてください✨

【NG】
- 冒頭フレーズなしの投稿（必ず先頭に「{opening}」が来ること）
- 70文字を超える長文
- 絵文字を6個以上使う
- 説明的・冗長な文章

【出力】
投稿文1パターンのみ出力。説明・前置き・結びの言葉は絶対不要。"""

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.strip()
    text = text.replace("「", "").replace("」", "")
    text = text.replace("。", "").replace("、", " ")

    if not text.startswith(opening):
        text = opening + " " + text

    return text

def post_to_threads(text, media_url=None, media_type=None):
    if media_type == "IMAGE":
        params = {"media_type": "IMAGE", "image_url": media_url, "text": text, "access_token": ACCESS_TOKEN}
        wait_sec = 30
    elif media_type == "VIDEO":
        params = {"media_type": "VIDEO", "video_url": media_url, "text": text, "access_token": ACCESS_TOKEN}
        wait_sec = 60
    else:
        params = {"media_type": "TEXT", "text": text, "access_token": ACCESS_TOKEN}
        wait_sec = 5

    r = requests.post(f"https://graph.threads.net/v1.0/{USER_ID}/threads", params=params)
    if r.status_code != 200:
        print(f"❌ コンテナ作成失敗: {r.text}")
        if media_type:
            print("📝 テキストのみで再試行")
            return post_to_threads(text, None, None)
        return r

    cid = r.json().get("id")
    print(f"✅ コンテナ作成: {cid}")
    print(f"⏳ {wait_sec}秒待機...")
    time.sleep(wait_sec)

    return requests.post(
        f"https://graph.threads.net/v1.0/{USER_ID}/threads_publish",
        params={"creation_id": cid, "access_token": ACCESS_TOKEN}
    )

if not ACCESS_TOKEN or not USER_ID:
    print("⚠️ Secrets未設定")
    exit(1)

text = generate_post()
print(f"📝 投稿文 ({len(text)}文字):\n{text}\n")

media_url, media_type = get_media()
if media_url:
    print(f"🎬 MEDIA_CHOSEN: type={media_type} url={media_url}")
else:
    print("📄 メディアなし")

r = post_to_threads(text, media_url, media_type)
if r.status_code == 200:
    print(f"✅ SUCCESS")
else:
    print(f"❌ FAILED: {r.status_code} {r.text}")
