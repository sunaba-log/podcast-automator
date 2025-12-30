import os

from services import AudioAnalyzer

project_id = os.environ.get("PROJECT_ID", "taka-test-481815")
gcs_uri = os.environ.get(
    "AUDIO_FILE_URL", "gs://sample-audio-for-sunabalog/short_dialogue.m4a"
)
model_id = os.environ.get("AI_MODEL_ID", "gemini-2.5-flash")
bucket_name = os.environ.get("BUCKET_NAME", "podcast")


# === スクリプト開始 ===
def main():
    # AudioAnalyzerの初期化
    analyzer = AudioAnalyzer(project_id=project_id)

    # 文字起こしを生成
    transcript = analyzer.generate_transcript(gcs_uri=gcs_uri, model_id=model_id)
    print("Transcript:")
    print(transcript)

    # 文字起こしを要約
    if transcript:
        summary = analyzer.summarize_transcript(
            transcript=transcript,
        )
    else:
        msg = "Error: transcript is None"
        raise ValueError(msg)
    print("\nSummary:")
    print(summary)


if __name__ == "__main__":
    main()
