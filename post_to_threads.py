import anthropic, requests, os, random, time


# === 過去5日間と同じ動画を使わない仕組み (auto-injected) ===
import json as _json_dedup
import os as _os_dedup
import datetime as _dt_dedup

_HISTORY_PATH = "state/used_videos_history.json"
_HISTORY_KEEP_DAYS = 5

def _load_history():
    if _os_dedup.path.exists(_HISTORY_PATH):
        try:
            return _json_dedup.loads(open(_HISTORY_PATH).read())
        except Exception:
            return []
    return []

def _save_history(history):
    _os_dedup.makedirs(_os_dedup.path.dirname(_HISTORY_PATH), exist_ok=True)
    with open(_HISTORY_PATH, "w") as f:
        _json_dedup.dump(history, f, ensure_ascii=False, indent=2)

def pick_unique_url(all_urls):
    """過去5日間に使ったURLを除外して選ぶ。全部被ったらリセット。"""
    history = _load_history()
    today = _dt_dedup.date.today()
    cutoff = today - _dt_dedup.timedelta(days=_HISTORY_KEEP_DAYS)
    recent = [h for h in history if h.get("date", "") > cutoff.isoformat()]
    used = {(h["url"][0] if isinstance(h["url"], (list, tuple)) else h["url"]) for h in recent}
    candidates = [u for u in all_urls if u[0] not in used]
    if not candidates:
        candidates = all_urls
    chosen = random.choice(candidates)
    recent.append({"date": today.isoformat(), "url": chosen[0]})
    _save_history(recent[-(_HISTORY_KEEP_DAYS + 1):])
    print(f"[dedup] 選択: {chosen[0]} (除外{len(used)}件/候補{len(candidates)}件)")
    return chosen
# === /5日間重複防止 ===


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
        return pick_unique_url(videos)
    return None, None

# === 投稿メニュー設定（ランチャーのボタンで切替 / config/menus.json） ===
import json as _mjson, os as _mos, datetime as _mdt
MENU_CONFIG_PATH = "config/menus.json"
_MENU_STATE_PATH = "state/last_menu.json"
DEFAULT_MENUS = ["ドライヘッドスパ","アロママッサージ","小顔矯正コルギ"]

MENU_SPECS = {
    "ドライヘッドスパ": {
        "label": "ドライヘッドスパ（70分3,980円）",
        "price_rule": "- 金額を出すなら「70分3,980円」だけ（ドライヘッドスパの回なので価格訴求はOK）",
        "examples": [
            "関西の人で70分3,980円のドライヘッドスパ受けたい人いますかー？🙋‍♀️寝落ち率95%です😴💤",
            "京都の人で頭が重い人いませんか👀ドライヘッドスパでスッキリしましょ✨",
            "京都の人で寝落ちしちゃうヘッドスパ受けませんか🐑💤全力で施術させていただきます🪽",
        ],
        "fallback": [
            "70分3,980円のドライヘッドスパで頭からスッキリしませんか😴💤✨",
            "頭が重い人いませんかー🙋‍♀️ドライヘッドスパで寝落ちしましょ🐑💤",
        ],
    },
    "アロママッサージ": {
        "label": "アロママッサージ",
        "price_rule": "- 金額（3,980円・¥3,980など）と「70分」などの分数は絶対に書かない",
        "examples": [
            "関西の人でアロママッサージ受けたい人✋いい香りでリラックスしませんか🫧✨",
            "京都の人で疲れ溜まってる人いませんかー🙋‍♀️アロマで一日の疲れリセットしましょ🥰",
            "京都の人で香りに癒されたい人いませんか🫧アロママッサージでほっと一息つきましょ💆✨",
        ],
        "fallback": [
            "アロママッサージでほっと一息つきませんか🫧✨",
            "疲れ溜まってる人いませんかー🙋‍♀️アロマの香りでリラックスしましょ🫧💆",
        ],
    },
    "小顔矯正コルギ": {
        "label": "小顔矯正コルギ",
        "price_rule": "- 金額（3,980円・¥3,980など）と「70分」などの分数は絶対に書かない",
        "examples": [
            "京都の人で小顔になりたい人いませんかー🙋‍♀️コルギで顔まわりスッキリさせますよ✨",
            "関西の人でむくみが気になる人👀小顔矯正コルギでフェイスラインすっきりしましょ🤩",
            "京都の人で写真映り変えたい人✋コルギで小顔目指しませんか✨💆",
        ],
        "fallback": [
            "小顔になりたい人いませんかー🙋‍♀️コルギでフェイスラインすっきりしましょ✨",
            "むくみが気になる人👀小顔矯正コルギで顔まわりスッキリしませんか🤩",
        ],
    },
    "もみほぐし": {
        "label": "もみほぐし",
        "price_rule": "- 金額（3,980円・¥3,980など）と「70分」などの分数は絶対に書かない",
        "examples": [
            "京都の人で肩こりつらい人いませんかー🙋‍♀️もみほぐしでしっかりほぐしますー💆✨",
            "関西の人でデスクワークで肩バキバキな人✋もみほぐしで軽くなりましょ🥰",
            "京都の人で体ガチガチな人いませんか👀もみほぐしでコリほぐしましょ🔥",
        ],
        "fallback": [
            "肩こりつらい人いませんかー🙋‍♀️もみほぐしでしっかりほぐしますー💆✨",
            "体ガチガチな人✋もみほぐしでスッキリ軽くなりましょ🥰",
        ],
    },
}

# 性的・官能的に読める表現（生成文に含まれていたら作り直す）
NG_WORDS = [
    "とろとろ", "トロトロ", "とろける", "トロける", "とろけ", "蕩",
    "私の手", "わたしの手", "この手で", "手で癒", "手でほぐ",
    "気持ちよく", "気持ち良く", "気持ちいい", "気持ち良い",
    "身を委ね", "委ねて", "虜", "骨抜き", "密着", "二人きり", "ふたりきり",
    "イかせ", "昇天", "快感", "官能", "エロ", "えっち", "エッチ", "ご奉仕", "奉仕",
    "全身を", "全身とろ", "隅々まで", "すみずみまで", "夜のお供", "癒させて",
]


def _has_ng(text):
    return any(w in text for w in NG_WORDS)


def load_menus():
    """config/menus.json で選ばれているメニューを返す（なければ DEFAULT_MENUS）"""
    try:
        with open(MENU_CONFIG_PATH, encoding="utf-8") as f:
            data = _mjson.load(f)
        menus = [m for m in data.get("menus", []) if m in MENU_SPECS]
        if menus:
            return menus
    except Exception:
        pass
    return [m for m in DEFAULT_MENUS if m in MENU_SPECS] or list(MENU_SPECS.keys())


def pick_menu():
    """選択中メニューからランダム。直前と同じメニューにはならない。"""
    menus = load_menus()
    last = None
    try:
        with open(_MENU_STATE_PATH, encoding="utf-8") as f:
            last = _mjson.load(f).get("menu")
    except Exception:
        last = None
    candidates = [m for m in menus if m != last] or menus[:]
    chosen = random.choice(candidates)
    try:
        _mos.makedirs(_mos.path.dirname(_MENU_STATE_PATH), exist_ok=True)
        with open(_MENU_STATE_PATH, "w", encoding="utf-8") as f:
            _mjson.dump({"menu": chosen, "date": _mdt.date.today().isoformat()}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    print(f"🧴 選択中メニュー: {menus} → 今回: {chosen}")
    return chosen


def generate_post():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    opening = random.choice(OPENING_PHRASES)
    menu = pick_menu()
    spec = MENU_SPECS[menu]
    if menu == "ドライヘッドスパ":
        ng_price = "- 3,980円以外の金額を書く"
    else:
        ng_price = "- 金額や分数を書く（ドライヘッドスパ以外は価格を一切出さない）"
    examples = "\n".join("- " + e for e in spec["examples"])

    prompt = f"""ヘッドミント京都祇園店（ドライヘッドスパ専門のリラクゼーションサロン）で働く若い女性セラピスト「ななみアビゲイル」として、Threadsの短い営業投稿を作成してください。

【絶対ルール】
- 投稿は **必ず以下の冒頭フレーズで始める**: 「{opening}」
- メニューは「{spec['label']}」を訴求する
{spec['price_rule']}
- 文字数は40〜70文字
- 句読点（。、）は使わず、絵文字や改行で区切る
- ハッシュタグは絶対なし
- 改行は1〜2回程度
- 絵文字は以下から3〜5個だけ使う: ✋ 😴 🫧 🙋‍♀️ 🪽 🐑 💤 👀 🥰 🤩 ❓ ✨ 🔥 💆
- 若い女性セラピストの明るい口調（〜ですー、〜ませんか、〜しましょ等）

【表現ルール（最重要）】
- 健全なリラクゼーションサロンの投稿にする。性的・官能的・意味深に受け取られる表現は一切使わない
- 「私の手で」「この手で」「とろとろ」「とろける」「気持ちよく」「身を委ねて」「全身を〜してあげる」「虜」「骨抜き」「密着」「二人きり」「癒させて」のような、セラピストの手や体・お客様の体の反応を強調する言い回しは禁止
- 訴求するのは「お客様の悩み（疲れ・肩こり・むくみ・頭の重さ・寝不足など）」と「メニューの効果（スッキリ・リラックス・小顔・寝落ち）」だけ

【冒頭フレーズの位置】
冒頭フレーズ「{opening}」は必ず投稿の最初に配置すること。

【参考にする投稿例（冒頭フレーズ部分は差し替えて使う）】
{examples}

【NG】
- 冒頭フレーズなしの投稿（必ず先頭に「{opening}」が来ること）
- 70文字を超える長文
- 絵文字を6個以上使う
- 説明的・冗長な文章
- 上の表現ルールに反する言い回し
{ng_price}

【出力】
投稿文1パターンのみ出力。説明・前置き・結びの言葉は絶対不要。"""

    text = ""
    for attempt in range(3):
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
        if not _has_ng(text):
            return text
        print(f"⚠️ NG表現を検出したので作り直し ({attempt + 1}/3): {text}")

    text = opening + " " + random.choice(spec["fallback"])
    print(f"🛟 安全な定型文を使用: {text}")
    return text
# === /投稿メニュー設定 ===


def post_to_threads(text, media_url=None, media_type=None):
    if media_type == "IMAGE":
        params = {"media_type": "IMAGE", "image_url": media_url, "text": text, "access_token": ACCESS_TOKEN}
    elif media_type == "VIDEO":
        params = {"media_type": "VIDEO", "video_url": media_url, "text": text, "access_token": ACCESS_TOKEN}
    else:
        params = {"media_type": "TEXT", "text": text, "access_token": ACCESS_TOKEN}

    r = requests.post(f"https://graph.threads.net/v1.0/{USER_ID}/threads", params=params)
    if r.status_code != 200:
        print(f"❌ コンテナ作成失敗: {r.text}")
        if media_type:
            print("📝 テキストのみで再試行")
            return post_to_threads(text, None, None)
        return r

    cid = r.json().get("id")
    print(f"✅ コンテナ作成: {cid}")

    # 動画の場合はステータスをポーリング（最大5分）
    if media_type == "VIDEO":
        for i in range(30):
            time.sleep(10)
            try:
                status_r = requests.get(
                    f"https://graph.threads.net/v1.0/{cid}",
                    params={"fields": "status,error_message", "access_token": ACCESS_TOKEN}
                )
                status_data = status_r.json()
                status = status_data.get("status", "")
                print(f"動画処理ステータス ({i+1}/30): {status}")
                if status == "FINISHED":
                    print("✅ 動画処理完了")
                    break
                if status == "ERROR":
                    err_msg = status_data.get("error_message", "Unknown error")
                    print(f"❌ 動画処理エラー: {err_msg}")
                    print("📝 テキストのみで再試行")
                    return post_to_threads(text, None, None)
            except Exception as e:
                print(f"ステータス確認エラー: {e}")
        else:
            print("⚠️ 動画処理タイムアウト（5分）、それでも公開を試みる")
    else:
        # 画像/テキストは短い待機でOK
        wait_sec = 30 if media_type == "IMAGE" else 5
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
