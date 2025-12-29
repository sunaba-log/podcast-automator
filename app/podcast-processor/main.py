import mimetypes
import os
import sys

from services import (
    AudioAnalyzer,
    GCSClient,
    Notifier,
    PodcastRssManager,
    R2Client,
    SecretManagerClient,
    transfer_gcs_to_r2,
)

# cloud run jobs
# https://docs.cloud.google.com/run/docs/quickstarts/jobs/build-create-python?hl=ja

PROJECT_ID = os.environ.get("PROJECT_ID", "taka-test-481815")
SECRET_NAME = os.environ.get("SECRET_NAME", "sunabalog-r2")
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "podcast")
SUBDIRECTORY = os.environ.get("SUBDIRECTORY", "test")  # R2内の保存先フォルダ
AUDIO_FILE_URL = os.environ.get(
    "AUDIO_FILE_URL", "gs://sample-audio-for-sunabalog/short_dialogue.m4a"
)  # GCSにアップロードされたmp3,m4aファイル名
AI_MODEL_ID = os.environ.get("AI_MODEL_ID", "gemini-2.5-flash")  # GeminiモデルID（未指定時はデフォルト）
R2_CUSTOM_DOMAIN = os.environ.get(
    "CUSTOM_DOMAIN", "podcast.sunabalog.com"
)  # R2のカスタムドメイン（未指定時はエンドポイントURL）

# 環境変数の確認
print("## Environment Variables ##")
print(f"PROJECT_ID: {PROJECT_ID}")
print(f"SECRET_NAME: {SECRET_NAME}")
print(f"R2_ENDPOINT_URL: {R2_ENDPOINT_URL}")
print(f"BUCKET_NAME: {BUCKET_NAME}")
print(f"SUBDIRECTORY: {SUBDIRECTORY}")
print(f"AUDIO_FILE_URL: {AUDIO_FILE_URL}")
print(f"AI_MODEL_ID: {AI_MODEL_ID}")
print(f"R2_CUSTOM_DOMAIN: {R2_CUSTOM_DOMAIN}")
print("###########################\n")


def process_podcast_workflow():
    """GCSへのファイルアップロードをトリガーに実行されるメイン関数"""
    # AUDIO_FILE_URL None チェック
    if not AUDIO_FILE_URL:
        print("Error: AUDIO_FILE_URL is not set.")
        return

    gcs_uri = AUDIO_FILE_URL
    print(f"\n## Start processing: {gcs_uri} ##")
    # GCS URI からバケット名とファイル名を抽出
    parts = gcs_uri.replace("gs://", "").split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    gcs_bucket_name, gcs_file_name = parts
    print(f"GCS Bucket: {gcs_bucket_name}, File: {gcs_file_name}")
    fn, audio_ext = os.path.splitext(gcs_file_name)
    # Mime Type 判定（タイトル等のメタデータ取得用）
    mime_type = mimetypes.guess_type(gcs_file_name)[0] or "audio/x-m4a"
    print(f"Detected mime type: {mime_type}")

    # secret manager から R2 と Discord の認証情報を取得
    secret_manager_client = SecretManagerClient(project_id=PROJECT_ID, secret_name=SECRET_NAME)
    r2_access_key, r2_secret_key = secret_manager_client.get_r2_credentials()
    discord_webhook_url = secret_manager_client.get_discord_webhook_url()
    notifier_client = Notifier(discord_webhook_url=discord_webhook_url)

    try:
        audio_analyzer = AudioAnalyzer(project_id=PROJECT_ID)
        r2_client = R2Client(
            project_id=PROJECT_ID,
            endpoint_url=R2_ENDPOINT_URL,
            bucket_name=BUCKET_NAME,
            access_key=r2_access_key,
            secret_key=r2_secret_key,
        )
        gcs_client = GCSClient(project_id=PROJECT_ID)

        # RSS feedからエピソード情報等を取得
        rss_feed = r2_client.download_file(f"{SUBDIRECTORY}/feed.xml")
        # byte -> str
        rss_feed = rss_feed.decode("utf-8")
        rss_manager = PodcastRssManager(rss_xml=rss_feed)
        latest_episode_number = rss_manager.get_total_episodes() + 1
        print(f"Latest Episode Number: {latest_episode_number}")

        # --- Phase 1: Fetch & Process (AI Analysis) ---
        # Vertex AIは GCS URI を直接読めるため、ダウンロード不要で分析可能
        print("\n## Step1: Running AI Analysis... ##")
        transcript = audio_analyzer.generate_transcript(gcs_uri, model_id=AI_MODEL_ID)
        summary = audio_analyzer.summarize_transcript(transcript, model_id=AI_MODEL_ID)
        print(f"Generated Summary: {summary}")
        summary.title = f"#{latest_episode_number} {summary.title}"

        # transcript と summary を保存しておくべきか
        # 保存する場合、R2 に保存するか GCS に保存するかを検討
        # 今回は保存せずWebhookで通知のみ
        notifier_client.send_discord_message(
            message=f"New Podcast Processed:\nTitle: {summary.title}\nDescription: {summary.description}"
        )

        # --- Phase 2: Upload to R2 ---
        print("\n## Step2: Uploading to Cloudflare R2... ##")
        # ストリームでGCSから取得し、R2へアップロード（ローカルディスク節約）
        public_url, file_size_bytes, duration_str = transfer_gcs_to_r2(
            gcs_client=gcs_client,
            r2_client=r2_client,
            gcs_bucket_name=gcs_bucket_name,
            gcs_object_name=gcs_file_name,
            r2_remote_key=f"{SUBDIRECTORY}/ep/{latest_episode_number}/audio{audio_ext}",
            content_type=mime_type,
            public=True,
            custom_domain=R2_CUSTOM_DOMAIN,
        )
        print(f"Uploaded audio to R2: {public_url}, Size: {file_size_bytes} bytes, Duration: {duration_str}")

        # --- Phase 3: Update RSS ---
        print("\n## Updating RSS Feed... ##")
        # rss file を R2 からダウンロードし、更新して再アップロード
        new_episode_data = {
            "title": summary.title,
            "description": summary.description,
            "audio_url": public_url,
            "duration": duration_str,
            "creator": "Sunaba Log",
            "file_size": file_size_bytes,
            "mime_type": mime_type,
            "episode_type": "full",
        }
        rss_manager.add_episode(new_episode_data)
        rss_xml = rss_manager.get_rss_xml()
        rss_xml_obj = rss_xml.encode("utf-8")
        r2_client.upload_file(
            file_content=rss_xml_obj,
            remote_key=f"{SUBDIRECTORY}/feed.xml",
            content_type="application/rss+xml; charset=utf-8",
            public=True,
        )

        # --- Phase 4: Notify Success ---
        print("\n## Notifying Discord (Success)... ##")
        notifier_client.send_discord_message(
            message=f"Podcast Episode Published Successfully:\nTitle: {summary.title}\nURL: {public_url}"
        )

    except Exception as e:
        print(f"Error occurred: {e}")
        notifier_client.send_discord_message(message=f"Podcast Processing Failed:\nError: {e}")


def main():
    """clound run jobs のエントリポイント"""
    for arg in sys.argv:
        print(arg)
    process_podcast_workflow()


if __name__ == "__main__":
    main()
