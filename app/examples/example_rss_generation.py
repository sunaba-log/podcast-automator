"""
PodcastRssGeneratorの使用例スクリプト
既存のRSS XMLから抽出した値を使用
"""

from services import PodcastRssManager

# === 既存RSS XMLから抽出した値 ===
PODCAST_TITLE = "sunabalog"
PODCAST_DESCRIPTION = """「妄想」から「現実」へ繋がるアイディエーション番組。
「1ヶ月で何かは作る」という具体的な目標を掲げ、アイデアの生成から実装までを追います。前半で自由なアイデアを議論し、後半ではそれを現実に引き戻す形で、実際に物を作ったり、作らなかったりする過程を配信します。"""
PODCAST_LANGUAGE = "ja"
PODCAST_CATEGORY = "Technology"
PODCAST_COVER_URL = "https://d3t3ozftmdmh3i.cloudfront.net/staging/podcast_uploaded_nologo/44930391/44930391-1766196120654-b1b62f088781f.jpg"
PODCAST_OWNER_NAME = "Sunaba Log"
PODCAST_OWNER_EMAIL = "noreply@sunabalog.com"  # メールアドレス(required)
PODCAST_AUTHOR = "Sunaba Log"
PODCAST_COPYRIGHT = "Sunaba Log"

# === スクリプト開始 ===
# ============================================================================
# === パート1: 新規RSSフィードの生成 ===
# ============================================================================

# 1. 新規作成
generator = PodcastRssManager()
rss = generator.generate_podcast_rss(
    title=PODCAST_TITLE,
    description=PODCAST_DESCRIPTION,
    language=PODCAST_LANGUAGE,
    category=PODCAST_CATEGORY,
    cover_url=PODCAST_COVER_URL,
    owner_name=PODCAST_OWNER_NAME,
    owner_email=PODCAST_OWNER_EMAIL,
    rss_link="https://sunabalog.com/rss.xml",
    author=PODCAST_AUTHOR,
    copyright_text=PODCAST_COPYRIGHT,
)

# 2. エピソード追加(複数エピソード)
# エピソード #3
generator.add_episode(
    {
        "title": "#3 脱・エグレス破産！音声ホスティングの救世主「Cloudflare R2」採用と、爆速MVP開発への技術的決断",
        "description": "GCPアカウント作成は「Googleグループ」ではできない/静かなるコスト爆弾：「エグレス破産」の恐怖/AIも教えてくれなかった救世主：Cloudflare R2と「出口料金ゼロ」という革命/便利さとのトレードオフ：自前でRSSフィードを育てる覚悟/未来のためのアーキテクチャ：なぜ「モノリシック」な設計を避けたのか",
        "audio_url": "https://anchor.fm/s/10c66ec7c/podcast/play/112773698/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2025-11-17%2Fb3d16db7-5221-63bc-50a9-45257599728f.m4a",
        "itunes_duration": "00:52:37",
        "guid": "5e8dfcde-2e6b-42d8-b19f-df701c06c607",
        "creator": "Sunaba Log",
        "file_size": 43352371,
        "mime_type": "audio/x-m4a",
        "itunes_episode_type": "full",
        "creator": "Sunaba Log",
    }
)

# エピソード #2
generator.add_episode(
    {
        "title": "#2 再生数8回からの挑戦！GCP×Geminiでポッドキャスト配信を全自動化する計画、始動。",
        "description": "今回のスナバログは、記念すべき第1回配信の「振り返り」と、エンジニアらしく「配信作業を技術で解決しよう」という自動化プロジェクトの立ち上げについてお話ししています。",
        "audio_url": "https://anchor.fm/s/10c66ec7c/podcast/play/112420592/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2025-11-10%2F737377b8-a23b-f03a-6494-bfef8be65248.m4a",
        "itunes_duration": "00:50:05",
        "guid": "b23c635e-c715-4703-9db7-33ecd566c18d",
        "creator": "Sunaba Log",
        "file_size": 40892218,
        "mime_type": "audio/x-m4a",
        "itunes_episode_type": "full",
    }
)

# エピソード #1
generator.add_episode(
    {
        "title": "#1 チャンネル名「Sunaba log」ついに決定！「妄想と実装」を掲げるアイディエーション型ポッドキャストのコンセプトを詰める",
        "description": "私たちが目指すポッドキャストの核となるコンセプトを改めて議論し、ついにチャンネル名を決定しました。",
        "audio_url": "https://anchor.fm/s/10c66ec7c/podcast/play/112112229/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2025-11-4%2F51f353e1-05a3-0312-4020-56e1b370a870.m4a",
        "itunes_duration": "00:34:15",
        "guid": "c88943a0-c88a-49f1-8a20-d23cc8ccf637",
        "creator": "Sunaba Log",
        "file_size": 24787780,
        "mime_type": "audio/x-m4a",
        "itunes_episode_type": "full",
        "itunes_season": 1,
        "itunes_episode_number": 1,
        "itunes_explicit": "no",
        "itunes_image": "https://d3t3ozftmdmh3i.cloudfront.net/staging/podcast_uploaded_nologo/44930391/44930391-176ç6196120654-b1b62f088781f.jpg",
    }
)

# 3. タイトル更新(オプション)
generator.update_title("Updated Podcast Title")

# 4. XML取得
xml = generator.get_rss_xml()
print(generator.get_total_episodes(), "エピソード数を生成済み")

# 5. 結果の表示(オプション)
# print(xml)

# または、ファイルに保存
with open("./examples/output/output_rss_feed.xml", "w", encoding="utf-8") as f:
    f.write(xml)
print("\n✅ RSS feed generated and saved to examples/output/output_rss_feed.xml")

# ============================================================================
# === パート2: 生成されたRSSフィードを読み込んで、更新メソッドをテスト ===
# ============================================================================

print("\n" + "=" * 80)
print("パート2: RSS フィードの更新テスト")
print("=" * 80 + "\n")

# 1. 既存のRSSフィードを読み込む
with open("./examples/output/output_rss_feed.xml", encoding="utf-8") as f:
    existing_rss = f.read()

# 2. 読み込んだRSSでジェネレータを初期化
generator_updated = PodcastRssManager(rss_xml=existing_rss)
print(generator_updated.get_total_episodes(), "エピソード数を読み込み済み")

# 3. タイトルを更新
print("📝 タイトルを更新中...")
generator_updated.update_title("sunabalog - 更新版")

# 4. 説明を更新
print("📝 説明を更新中...")
new_description = """「妄想」から「現実」へ繋がるアイディエーション番組。
「1ヶ月で何かは作る」という具体的な目標を掲げ、アイデアの生成から実装までを追います。
前半で自由なアイデアを議論し、後半ではそれを現実に引き戻す形で、実際に物を作ったり、作らなかったりする過程を配信します。

[更新版] このRSSは更新テストのために変更されました。"""
generator_updated.update_description(new_description)

# 5. カテゴリを更新
print("📝 カテゴリを更新中...")
generator_updated.update_category("Business")
print("📝 カテゴリを更新完了:", generator_updated.get_rss_xml()[800:1500])

# 6. エピソードを更新
print("📝 エピソード #3 を更新中...")
generator_updated.update_episode(
    episode_id="5e8dfcde-2e6b-42d8-b19f-df701c06c607",
    updated_data={
        "title": "#3 脱・エグレス破産！音声ホスティングの救世主「Cloudflare R2」採用と、爆速MVP開発への技術的決断 [更新]",
        "description": "GCPアカウント作成は「Googleグループ」ではできない/静かなるコスト爆弾：「エグレス破産」の恐怖/AIも教えてくれなかった救世主：Cloudflare R2と「出口料金ゼロ」という革命/便利さとのトレードオフ：自前でRSSフィードを育てる覚悟/未来のためのアーキテクチャ：なぜ「モノリシック」な設計を避けたのか\n\n[更新版] このエピソードは更新テストのために変更されました。",
    },
)
print("📝 エピソード #3 を更新完了:", generator_updated.get_rss_xml()[800:1500])

# 7. 新しいエピソードを追加
print("📝 新しいエピソードを追加中...")
generator_updated.add_episode(
    {
        "title": "#4 [新規] RSS更新テスト - 新しいエピソード追加",
        "description": "このエピソードはRSSフィード更新テストの一環として新しく追加されたものです。",
        "audio_url": "https://example.com/episodes/episode-4.m4a",
        "duration": "00:10:00",
        "creator": "Sunaba Log",
        "file_size": 1000000,
        "mime_type": "audio/x-m4a",
        "episode_type": "full",
        "episode_art_url": f"https://example.com/ep-art4.jpg",
        "category": "Technology",
        "season": 1,
        "episode_number": 4,
        "explicit": "no",
    }
)

# 8. 更新されたXMLを取得
updated_xml = generator_updated.get_rss_xml()
print(generator_updated.get_total_episodes(), "エピソード数を更新済み")

# 9. 更新されたXMLをファイルに保存
with open("./examples/output/output_rss_feed_updated.xml", "w", encoding="utf-8") as f:
    f.write(updated_xml)
print("\n✅ 更新されたRSS feed を保存: examples/output/output_rss_feed_updated.xml")

print("\n" + "=" * 80)
print("✨ すべての更新テストが完了しました！")
print("=" * 80)
print("\n📊 実行内容:")
print("  1. タイトルを更新")
print("  2. 説明を更新")
print("  3. カテゴリを更新 (Technology → Business)")
print("  4. エピソード #3 を更新")
print("  5. 新しいエピソード #4 を追加")
print("\n📁 出力ファイル:")
print("  - output/output_rss_feed.xml (元のフィード)")
print("  - output/output_rss_feed_updated.xml (更新済みフィード)")
