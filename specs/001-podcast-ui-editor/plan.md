# 実装計画: Podcast UI編集・配信素材管理

**ブランチ**: `001-podcast-ui-editor` | **日付**: 2026年2月15日 | **Spec**: [specs/001-podcast-ui-editor/spec.md](specs/001-podcast-ui-editor/spec.md)
**入力**: /specs/001-podcast-ui-editor/spec.md の仕様書

**注意**: このテンプレートは `/speckit.plan` コマンドで埋められます。
実行フローは `.specify/templates/commands/plan.md` を参照してください。

## 概要

ローカル運用者向けに、Cloudflare R2 上のRSSフィードを取得・編集し、番組/エピソード情報、アートワーク、音声ファイルの差し替えと再公開を行う管理UIを提供する。RSS更新前に自動バックアップを保存し、番組/エピソードの説明文プレビューを提供する。UIはReact系で構築し、バックエンドはPython APIとして既存のRSS/R2ロジックを再利用する。設計上はNext.js(App Router)のUIとFastAPIのAPIを分離し、ローカル実行時に簡易パスワードで保護する。

## 技術コンテキスト

<!--
  必須: このセクションはプロジェクトに合わせて置き換えてください。
-->

**言語/バージョン**: Python 3.12, TypeScript 5.x  
**主要依存**: FastAPI, Uvicorn, Next.js(App Router), React, shadcn/ui, Tailwind CSS, boto3, feedparser, feedgen  
**ストレージ**: Cloudflare R2（RSS/メディア）, ローカルファイルキャッシュ（RSS/バックアップ/一時ファイル）  
**テスト**: pytest, vitest + React Testing Library  
**対象プラットフォーム**: ローカルWebアプリ（macOS/Linux）
**プロジェクト種別**: web（frontend + backend）  
**性能目標**: RSS取得と一覧表示が100エピソードで5秒以内、UI操作レスポンス1秒以内  
**制約**: DB不使用、単一運用者、簡易パスワード認証、R2のみ利用、RSS上書き前のバックアップ必須  
**規模/スコープ**: 1番組/数百エピソード程度、同時利用1人

## 憲法チェック

*GATE: Phase 0 調査前に必須。Phase 1 設計後にも再確認。*

- [x] TypeScript/Pythonのクリーンコード方針に適合している
- [x] TypeScript/Pythonのユニットテストが必須として計画されている
- [x] UI/UXの一貫性（既存パターン準拠）が明記されている
- [x] ドキュメント/Issue/PRが日本語運用である

### 憲法チェック（Phase 1後 再確認）

- [x] TypeScript/Pythonのクリーンコード方針に適合している
- [x] TypeScript/Pythonのユニットテストが必須として計画されている
- [x] UI/UXの一貫性（既存パターン準拠）が明記されている
- [x] ドキュメント/Issue/PRが日本語運用である

## プロジェクト構成

### ドキュメント（本機能）

```text
specs/001-podcast-ui-editor/
├── plan.md              # 本ファイル (/speckit.plan 出力)
├── research.md          # Phase 0 出力 (/speckit.plan)
├── data-model.md        # Phase 1 出力 (/speckit.plan)
├── quickstart.md        # Phase 1 出力 (/speckit.plan)
├── contracts/           # Phase 1 出力 (/speckit.plan)
└── tasks.md             # Phase 2 出力 (/speckit.tasks - /speckit.plan では作成されない)
```

### ソースコード（リポジトリルート）
<!--
  必須: 以下のツリーを実際の構成に置き換えてください。
  使用しない選択肢は削除し、Option 表記は残さない。
-->

```text
api/                    # FastAPI 新規追加予定

web/                    # Next.js UI 新規追加予定
├── src/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── services/
└── tests/
```

**構成判断**: backend は既存の api/ に FastAPI API を追加し、frontend は web/ に Next.js を新設する。

## 複雑性トラッキング

> **憲法チェックで逸脱がある場合のみ記載**

| 違反 | 必要理由 | 単純案が不可な理由 |
|------|----------|---------------------|
