# Phase 0 Research: Podcast UI編集・配信素材管理

## Decision 1: フロントエンド基盤は Next.js(App Router)

- **Decision**: Next.js(App Router) + React + shadcn/ui + Tailwind CSS を採用する
- **Rationale**: 内部ツールでBFFと同居しやすく、ルーティング/レイアウト/認証周りが標準機能で扱えるため開発・運用コストが低い
- **Alternatives considered**: Vite + React（静的配布は容易だがAPI分離と認証実装の負担が増える）

## Decision 2: 音声アップロードとストリーミングの実装方針

- **Decision**: FastAPI の `UploadFile` + `multipart/form-data` を採用し、大容量はチャンク読みで処理する。再生用には `FileResponse` または `StreamingResponse` を用いる
- **Rationale**: `UploadFile` は大容量に適し、`FileResponse` はRange対応で音声再生に有利。フォームデータとファイルの同時送信が容易
- **Alternatives considered**: JSON + Base64 送信（サイズ増・メモリ負荷が大きく不適）

## Decision 3: Cloudflare R2 アクセス方法

- **Decision**: boto3 の S3 互換 API を使用し、アップロード時に Content-Type を必ず付与する。公開URLはカスタムドメインを前提とする
- **Rationale**: 既存の `R2Client` を再利用でき、S3互換の標準パターンで運用できる。カスタムドメインは公開用途に安定
- **Alternatives considered**: r2.dev 公開URL（開発用途限定でレート制限あり）
