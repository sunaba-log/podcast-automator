# Podcastの番組情報やチャンネル情報の編集、番組および各エピソードのアートワークの編集、音声アップロードをローカルアプリのUI上からできるようになる

## 機能要件

- CloudFlareR2でホストされ、公開されているRSSフィードを取得し、番組情報、エピソード情報、番組および各エピソードのアートワーク、音声ファイルを取得できるようにする。音声ファイルについてはDLせずに、ストリーミングするようにしても良い。
- UI上からRSSフィードを書き換えて、CloudFlare R2の認証情報を利用して再度アップロードすることができる。
- UI上からCloudFlare R2上の番組やエピソードのアートワーク（画像）をアップロードして、RSSフィードにそのURLを記載し、再度アップロードすることができる。
- UI上からapple podcast/ spotify / amazon music での説明文の見え方をプレビューできる。（RSSフィードではxmlで表現しており、HTMLコンテンツをエスケープ処理している部分があるため）
- UI上からCloudFlare R2音声ファイルを置換することができる。置換した際にURLが変更される場合はRSSフィードも変更してアップロードすることができる。

## その他要件

- UIはReactでshadcn/tailwindでコンポーネント管理できるようにする。
- バックエンドはpythonのfastapiなどを利用して、既存のライブラリを再利用できるようにする。
- ローカルでの検証時には認証情報は.envに記載し、RSSフィードや画像情報についてキャッシュが必要な場合もローカルに保存し、DBは利用しない。
- UIとapiの連携には、dockercomposeでサービスを立ち上げるようにしても良い。
- UIはNextjsを利用しても良い。そのほか適切なフレームワークがあれば採用しても良い。

## 画面遷移案

適切な構成に修正して下さい。

```sh
/ (Root Layout)
├── /dashboard (ダッシュボード・番組一覧)
│   └── [番組選択・新規作成ボタン(RSS　URL登録)]
│
└── /programs/:programId (番組管理ベースレイアウト)
    ├── /edit (番組基本情報編集)
    │   ├── [タイトル・説明文入力フォーム]
    │   └── [番組全体アートワーク編集]
    └── /episodes (エピソード一覧、エピソード検索・フィルタリング,新規エピソード作成)
        └── /:episodeId  (番組基本情報編集)
            ├── [配信ステータス変更（公開/下書き）]
            ├── [エピソード情報修正]
            ├── [エピソードアートワーク編集]
            └── [音声の差し替え・再生確認]
```

## 留意事項

可能であれば、Podcast Processor Agent (Cloud Run Job)`./app` ですでに実装されている機能を流用する。
Podcast Processor Agentの概要は以下の通り
---

Google Cloud Run Jobs 上で動作するポッドキャスト配信自動化エージェントです。
GCS (Google Cloud Storage) にアップロードされた音声ファイルをトリガーに、AI による分析、Cloudflare R2 へのホスティング、RSS フィードの更新、Discord 通知までを一貫して実行します。

ディレクトリ構成:

```sh
.
├── main.py              # エントリーポイント (ワークフロー定義)
├── services/            # 各種サービスクラス
│   ├── ai_analyzer.py   # Vertex AI 連携
│   ├── r2_client.py     # Cloudflare R2 操作
│   ├── rss_manager.py   # RSSフィード生成・更新
│   ├── rss_manager.py   # RSSフィード生成・更新
│   ├── notifier.py   # Discord への通知用
│   ├── storage.py   # Cloudflare R2, Google Cloud Storage 操作ライブラリ
│   └── audio_converter.py # Audio file converter service.
├── pyproject.toml       # 依存関係定義
├── uv.lock              # ロックファイル
└── Dockerfile           # コンテナ定義
```
