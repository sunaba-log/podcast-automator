"""descriptionとitunes:summaryの処理例を示すスクリプト."""

import sys
from pathlib import Path

# src ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services import PodcastRssManager


def main():
    """RSSフィードを生成してdescriptionとitunes:summaryの処理を確認."""
    # RSSマネージャーを初期化
    rss_manager = PodcastRssManager()

    # ポッドキャストを生成
    rss_manager.generate_podcast_rss(
        title="テストポッドキャスト",
        description="これはテストポッドキャストです",
        language="ja",
        category="Technology",
        cover_url="https://example.com/cover.jpg",
        owner_name="テストオーナー",
    )

    # HTMLタグを含むエピソードを追加
    html_content = """<p>このエピソードではHTML & XMLの違いについて説明します。</p>
<br>
<p>重要なポイント:</p>
<ul>
<li>HTML < XML</li>
<li>特殊文字 & エスケープ</li>
</ul>"""

    episode_data = {
        "title": "Episode 1: HTML & XML入門",
        "description": html_content,
        "itunes_summary": html_content,
        "audio_url": "https://example.com/episode1.mp3",
        "itunes_duration": "00:30:00",
        "file_size": 15000000,
    }

    rss_manager.add_episode(episode_data)

    # 生成されたRSS XMLを取得
    rss_xml = rss_manager.get_rss_xml()

    # 結果を表示
    print("=" * 80)
    print("生成されたRSS XML:")
    print("=" * 80)
    print(rss_xml)
    print("\n" + "=" * 80)
    print("検証結果:")
    print("=" * 80)

    # descriptionの確認
    if "<description><![CDATA[" in rss_xml and "<p>このエピソードでは" in rss_xml:
        print("✓ <description>はCDATAで囲まれ、HTMLタグがそのまま維持されています")
    else:
        print("✗ <description>の処理に問題があります")

    # itunes:summaryの確認
    if "&lt;p&gt;" in rss_xml and "&lt;ul&gt;" in rss_xml:
        print("✓ <itunes:summary>内のHTMLタグはXMLエスケープされています")
    else:
        print("✗ <itunes:summary>の処理に問題があります")

    # CDATA確認
    if "<itunes:summary><![CDATA[" not in rss_xml:
        print("✓ <itunes:summary>はCDATAで囲まれていません")
    else:
        print("✗ <itunes:summary>がCDATAで囲まれています（不正）")


if __name__ == "__main__":
    main()
