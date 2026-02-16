# Phase 1 Data Model: Podcast UI編集・配信素材管理

## Entity: Podcast

- **Purpose**: 番組の基本情報を保持する
- **Fields**:
  - `id`: string（RSS内のchannel識別子、またはURL由来のID）
  - `title`: string（必須）
  - `description`: string（必須）
  - `link`: string（任意）
  - `language`: string（例: ja）
  - `itunesAuthor`: string
  - `itunesCategory`: string
  - `itunesImageUrl`: string（番組アートワークURL）
  - `itunesExplicit`: string（yes/no/clean）
  - `ownerName`: string
  - `ownerEmail`: string
  - `rssUrl`: string（取得元/公開先のRSS URL）

- **Validation**:
  - `title`, `description` は必須
  - URLは `http/https` のみ許可

## Entity: Episode

- **Purpose**: エピソード情報と配信素材を保持する
- **Fields**:
  - `id`: string（guid）
  - `podcastId`: string（Podcast 参照）
  - `title`: string（必須）
  - `description`: string（必須）
  - `status`: enum(`draft`, `published`)
  - `audioUrl`: string（必須、R2 URL）
  - `audioSizeBytes`: number
  - `audioMimeType`: string（例: audio/mpeg）
  - `itunesDuration`: string（HH:MM:SS）
  - `itunesImageUrl`: string（任意）
  - `publishedAt`: datetime（任意）

- **Validation**:
  - `title`, `description`, `audioUrl` は必須
  - `itunesDuration` は `^\d{1,2}:\d{2}:\d{2}$`
  - `status` は `draft` or `published`

- **State transitions**:
  - `draft` → `published`（公開）
  - `published` → `draft`（非公開化、必要に応じて許可）

## Entity: MediaAsset

- **Purpose**: アートワーク/音声ファイルのメタデータ
- **Fields**:
  - `id`: string
  - `type`: enum(`podcast_artwork`, `episode_artwork`, `audio`)
  - `ownerId`: string（Podcast/Episode 参照）
  - `url`: string（R2 公開URL）
  - `contentType`: string（例: image/png, audio/mpeg）
  - `sizeBytes`: number
  - `updatedAt`: datetime

- **Validation**:
  - 画像は `image/png` or `image/jpeg` のみ許可
  - 音声は `audio/mpeg` or `audio/mp4` のみ許可

## Entity: RssFeed

- **Purpose**: RSSフィード本文と更新情報
- **Fields**:
  - `rssUrl`: string（取得/公開先）
  - `rawXml`: string
  - `fetchedAt`: datetime
  - `updatedAt`: datetime

- **Validation**:
  - `rawXml` は well-formed XML

## Entity: RssBackup

- **Purpose**: RSSのバックアップ履歴
- **Fields**:
  - `id`: string
  - `rssUrl`: string
  - `backupUrl`: string（R2保存先）
  - `createdAt`: datetime

- **Validation**:
  - 上書き前に必ず作成

## Entity: DistributionPreview

- **Purpose**: 配信先表示のプレビュー
- **Fields**:
  - `id`: string
  - `target`: enum(`podcast_description`, `episode_description`)
  - `sourceText`: string
  - `renderedHtml`: string

- **Validation**:
  - `sourceText` は RSS 仕様に準拠してエスケープ処理

## Relationships

- Podcast 1:N Episode
- Podcast 1:N MediaAsset（podcast_artwork）
- Episode 1:N MediaAsset（episode_artwork/audio）
- RssFeed 1:1 Podcast（取得元RSSに紐付く）
- RssBackup 1:N RssFeed
