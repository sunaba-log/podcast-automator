---
description: "機能実装用のタスクリスト"
---

# タスク: Podcast UI編集・配信素材管理

**入力**: /specs/001-podcast-ui-editor/ の設計ドキュメント
**前提**: plan.md（必須）、spec.md（ユーザーストーリー必須）、research.md、data-model.md、contracts/

**テスト**: ユニットテストは必須（pytest, vitest + React Testing Library）
**構成**: タスクはユーザーストーリー単位で整理し、各ストーリーを独立に実装・検証可能にする。

## Phase 1: セットアップ（共通基盤）

**目的**: 初期化と基本構造

- [ ] T001 API プロジェクト設定を初期化する in api/pyproject.toml
- [ ] T002 FastAPI エントリポイントとルータ基盤を作成する in api/src/main.py
- [ ] T003 Web プロジェクト設定を初期化する in web/package.json
- [ ] T004 Tailwind/shadcn 基本スタイルを追加する in web/tailwind.config.ts
- [ ] T005 [P] Pytest 設定を追加する in api/pytest.ini
- [ ] T006 [P] Vitest 設定を追加する in web/vitest.config.ts
- [ ] T007 [P] API 環境変数テンプレートを追加する in api/.env.example
- [ ] T008 [P] Web 環境変数テンプレートを追加する in web/.env.local.example
- [ ] T009 [P] API リント/フォーマット設定を追加する in api/pyproject.toml
- [ ] T010 [P] Web ESLint 設定を追加する in web/.eslintrc.cjs

---

## Phase 2: 基盤（ブロッキング前提）

**目的**: すべてのストーリーの前提となる基盤

**⚠️ 重要**: ここが完了するまでストーリー実装は開始しない

- [ ] T011 環境設定ローダを実装する in api/src/config.py
- [ ] T012 管理パスワード認証依存を実装する in api/src/middleware/auth.py
- [ ] T013 認証と例外ハンドリングを組み込む in api/src/main.py
- [ ] T014 Podcast スキーマを定義する in api/src/schemas/podcast.py
- [ ] T015 Episode スキーマを定義する in api/src/schemas/episode.py
- [ ] T016 RSS/Backup スキーマを定義する in api/src/schemas/rss.py
- [ ] T017 R2 クライアントラッパーを実装する in api/src/services/r2_client.py
- [ ] T018 RSS 取得/解析サービスを実装する in api/src/services/rss_parser.py
- [ ] T019 RSS バックアップサービスを実装する in api/src/services/rss_backup.py
- [ ] T020 エラー型と共通レスポンスを実装する in api/src/errors.py
- [ ] T021 ルータ登録の基盤を整備する in api/src/routers/**init**.py

**チェックポイント**: 基盤完成 → ストーリー実装を並行開始可能

---

## Phase 3: ユーザーストーリー1 - RSS取得と番組・エピソード編集（優先度: P1）🎯 MVP

**目標**: RSS を読み込み、番組/エピソードを編集して再公開できる

**独立テスト**: RSS URLを入力し、編集と再公開まで完結できる

### テスト（必須）

- [ ] T022 [P] [US1] RSS 取得/更新/公開のユニットテストを追加する in api/tests/test_rss_workflow.py
- [ ] T023 [P] [US1] UI 編集フローのユニットテストを追加する in web/tests/rss_editor.test.tsx

### 実装

- [ ] T024 [P] [US1] RSS 取り込み API を実装する in api/src/routers/feeds.py
- [ ] T025 [P] [US1] 番組情報取得/更新 API を実装する in api/src/routers/podcasts.py
- [ ] T026 [P] [US1] エピソード一覧/更新 API を実装する in api/src/routers/episodes.py
- [ ] T027 [US1] RSS 公開（バックアップ含む）サービスを実装する in api/src/services/rss_publisher.py
- [ ] T028 [US1] RSS 公開 API を実装する in api/src/routers/rss.py
- [ ] T029 [P] [US1] RSS URL 入力と読み込み画面を実装する in web/src/app/page.tsx
- [ ] T030 [P] [US1] 番組編集フォームを実装する in web/src/components/podcast-editor.tsx
- [ ] T031 [P] [US1] エピソード一覧と編集 UI を実装する in web/src/components/episode-list.tsx
- [ ] T032 [US1] エピソード検索/フィルタ UI を実装する in web/src/components/episode-filters.tsx
- [ ] T033 [US1] RSS/番組/エピソード API クライアントを実装する in web/src/services/api.ts

**チェックポイント**: ストーリー1が単独で機能・検証可能

---

## Phase 4: ユーザーストーリー2 - アートワークと音声の差し替え（優先度: P2）

**目標**: アートワーク/音声の差し替えと新規エピソード作成ができる

**独立テスト**: 任意エピソードでアートワーク/音声差し替えと新規追加ができる

### テスト（必須）

- [ ] T034 [P] [US2] メディアアップロードと新規作成のユニットテストを追加する in api/tests/test_media_upload.py
- [ ] T035 [P] [US2] 画像/音声アップロード UI のユニットテストを追加する in web/tests/media_upload.test.tsx

### 実装

- [ ] T036 [P] [US2] メディアアップロードサービスを実装する in api/src/services/media_uploader.py
- [ ] T037 [P] [US2] 番組アートワークアップロード API を実装する in api/src/routers/media.py
- [ ] T038 [P] [US2] エピソードのアートワーク/音声差し替え API を実装する in api/src/routers/media.py
- [ ] T039 [P] [US2] 新規エピソード作成 API を実装する in api/src/routers/episodes.py
- [ ] T040 [US2] メディア URL 反映の RSS ビルダを実装する in api/src/services/rss_builder.py
- [ ] T041 [P] [US2] アートワークアップロード UI を実装する in web/src/components/artwork-uploader.tsx
- [ ] T042 [P] [US2] 音声アップロード/差し替え UI を実装する in web/src/components/audio-uploader.tsx
- [ ] T043 [US2] 新規エピソード作成フォームを実装する in web/src/components/episode-create-form.tsx

**チェックポイント**: ストーリー2が単独で機能・検証可能

---

## Phase 5: ユーザーストーリー3 - 配信先表示のプレビュー（優先度: P3）

**目標**: 番組/エピソード説明のプレビューを表示できる

**独立テスト**: 任意の番組・エピソードでプレビュー表示ができる

### テスト（必須）

- [ ] T044 [P] [US3] プレビュー生成のユニットテストを追加する in api/tests/test_previews.py
- [ ] T045 [P] [US3] プレビュー UI のユニットテストを追加する in web/tests/preview_modal.test.tsx

### 実装

- [ ] T046 [P] [US3] プレビュー生成サービスを実装する in api/src/services/preview_renderer.py
- [ ] T047 [P] [US3] プレビュー API を実装する in api/src/routers/previews.py
- [ ] T048 [P] [US3] プレビュー表示モーダルを実装する in web/src/components/preview-modal.tsx
- [ ] T049 [US3] プレビュー操作を編集 UI に統合する in web/src/components/podcast-editor.tsx

**チェックポイント**: 全ストーリーが独立に機能

---

## Phase 6: 仕上げ & 横断課題

**目的**: 複数ストーリーにまたがる改善

- [ ] T050 [P] API/WEB の利用手順を更新する in api/README.md
- [ ] T051 [P] 失敗時のエラーバナー UI を追加する in web/src/components/error-banner.tsx
- [ ] T052 エピソード大量表示のパフォーマンス対策を追加する in web/src/components/episode-list.tsx
- [ ] T053 クイックスタート検証結果を追記する in specs/001-podcast-ui-editor/quickstart.md

---

## 依存関係と実行順序

### フェーズ依存

- **セットアップ（Phase 1）**: 依存なし
- **基盤（Phase 2）**: Phase 1 完了が前提
- **ストーリー（Phase 3+）**: Phase 2 完了が前提
- **仕上げ（Phase 6）**: 必要なストーリー完了が前提

### ストーリー依存

- **ストーリー1（P1）**: Phase 2 完了後に開始
- **ストーリー2（P2）**: Phase 2 完了後に開始（独立テスト可能）
- **ストーリー3（P3）**: Phase 2 完了後に開始（独立テスト可能）

### 各ストーリー内の順序

- テストを先に書き、失敗を確認してから実装
- サービス/スキーマ → エンドポイント → UI の順

---

## 並列例

### ストーリー1

- [P] T022 と T023 は並列に実行可能
- [P] T024 と T025 と T026 は並列に実行可能
- [P] T029 と T030 と T031 は並列に実行可能

### ストーリー2

- [P] T034 と T035 は並列に実行可能
- [P] T036 と T037 と T038 は並列に実行可能
- [P] T041 と T042 は並列に実行可能

### ストーリー3

- [P] T044 と T045 は並列に実行可能
- [P] T046 と T047 と T048 は並列に実行可能

---

## 実装戦略

### MVP優先（ストーリー1のみ）

1. Phase 1 完了
2. Phase 2 完了（ブロッキング）
3. Phase 3 完了
4. **停止して検証**: ストーリー1を単独テスト
5. デモ/運用準備

### 段階的デリバリ

1. 基盤完成
2. ストーリー1 → テスト → 確認
3. ストーリー2 → テスト → 確認
4. ストーリー3 → テスト → 確認

### 複数人の並列戦略

1. セットアップ + 基盤を全員で完了
2. 完了後にストーリーを分担

---

## Notes

- [P] = 別ファイル/依存なし
- [Story] = 追跡可能なストーリー紐付け
- 各ストーリーは独立して完成・検証可能であること
- 曖昧なタスク、同一ファイル競合、独立性を壊す依存は避ける
