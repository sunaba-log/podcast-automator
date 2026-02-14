# 実装計画: [FEATURE]

**ブランチ**: `[###-feature-name]` | **日付**: [DATE] | **Spec**: [link]
**入力**: `/specs/[###-feature-name]/spec.md` の仕様書

**注意**: このテンプレートは `/speckit.plan` コマンドで埋められます。
実行フローは `.specify/templates/commands/plan.md` を参照してください。

## 概要

[仕様からの要約: 主要要件 + 調査に基づく技術方針]

## 技術コンテキスト

<!--
  必須: このセクションはプロジェクトに合わせて置き換えてください。
-->

**言語/バージョン**: [例: Python 3.11, TypeScript 5.x または NEEDS CLARIFICATION]  
**主要依存**: [例: FastAPI, React など or NEEDS CLARIFICATION]  
**ストレージ**: [該当する場合のみ、例: PostgreSQL, ファイル, N/A]  
**テスト**: [例: pytest, vitest など or NEEDS CLARIFICATION]  
**対象プラットフォーム**: [例: Linux server, Web など or NEEDS CLARIFICATION]
**プロジェクト種別**: [single/web/mobile - 構成決定に使用]  
**性能目標**: [例: 1000 req/s, 60 fps など or NEEDS CLARIFICATION]  
**制約**: [例: <200ms p95, <100MB, offline 対応 など or NEEDS CLARIFICATION]  
**規模/スコープ**: [例: 10k users, 50 screens など or NEEDS CLARIFICATION]

## 憲法チェック

*GATE: Phase 0 調査前に必須。Phase 1 設計後にも再確認。*

- [ ] TypeScript/Pythonのクリーンコード方針に適合している
- [ ] TypeScript/Pythonのユニットテストが必須として計画されている
- [ ] UI/UXの一貫性（既存パターン準拠）が明記されている
- [ ] ドキュメント/Issue/PRが日本語運用である

## プロジェクト構成

### ドキュメント（本機能）

```text
specs/[###-feature]/
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
# [不要なら削除] Option 1: 単一プロジェクト（デフォルト）
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [不要なら削除] Option 2: Web アプリ（frontend + backend）
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [不要なら削除] Option 3: Mobile + API
api/
└── [backend 同等の構成]

ios/ or android/
└── [プラットフォーム固有の構成]
```

**構成判断**: [採用した構成と実際のディレクトリを記載]

## 複雑性トラッキング

> **憲法チェックで逸脱がある場合のみ記載**

| 違反 | 必要理由 | 単純案が不可な理由 |
|------|----------|---------------------|
| [例: 4つ目のプロジェクト] | [現在の必要性] | [3プロジェクトでは不足な理由] |
| [例: Repository パターン] | [具体的問題] | [直接アクセスが不可な理由] |
