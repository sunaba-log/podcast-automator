## ディレクトリ構造

### エピソード別

「文字起こしテキスト(.txt)」や「チャプターファイル(.json)」など、1 エピソードあたりのファイル数が増える可能性あり

```markdown
podcast.sunabalog.com/
├── <channel_id>/
│ ├── feed.xml
│ ├── artwork.jpg
│ └── ep/
│ ├── <number>/ # エピソードごとにディレクトリを切る
│ │ ├── audio.mp3 # ファイル名を固定できるメリットあり
│ │ ├── cover.jpg
│ │ └── transcript.txt # 将来的な拡張
│ └── <number_2>/
│ ├── audio.mp3
│ └── cover.jpg
```

## 参考

- [Directory>R2>Examples>S3 SDKs>boto3](https://developers.cloudflare.com/r2/examples/aws/boto3/)
