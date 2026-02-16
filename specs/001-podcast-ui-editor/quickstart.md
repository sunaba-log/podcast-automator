# Phase 1 Quickstart: Podcast UI編集・配信素材管理

## 目的

ローカル環境でUIとAPIを起動し、RSS読み込みから更新・再公開までの基本フローを確認する。

## 前提

- Cloudflare R2 のバケットと公開URL（カスタムドメイン推奨）
- RSS の公開URL
- ローカルでの簡易パスワード（`.env`）

## 環境変数（例）

- `R2_ENDPOINT_URL`
- `R2_BUCKET_NAME`
- `R2_ACCESS_KEY`
- `R2_SECRET_KEY`
- `R2_PUBLIC_BASE_URL`
- `RSS_URL`
- `ADMIN_PASSWORD`

## 起動手順（想定）

1. backend（FastAPI）を起動する
2. frontend（Next.js）を起動する
3. UI で `RSS_URL` を読み込み、番組/エピソードを表示する
4. 番組情報を更新して RSS を再公開する

## 動作確認チェック

- RSS の読み込みが成功し、番組/エピソードが表示される
- 番組情報の編集と再公開が成功する
- エピソードのアートワーク/音声の差し替えが反映される
- 説明文プレビューが番組/エピソードの両方で表示される
- RSS 上書き前にバックアップが作成される
