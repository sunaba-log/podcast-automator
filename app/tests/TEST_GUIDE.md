# Notifier テスト実行ガイド

## 必要な依存関係のインストール

```bash
# テスト用の依存関係をインストール
pip install pytest pytest-asyncio aiohttp
```

## テスト実行

### すべてのテストを実行

```bash
cd /Users/onotakayoshi/Documents/Projects/sunabalog/podcast-automator/app/podcast-processor
python -m pytest tests/test_notifier.py -v
```

### 特定のテストクラスを実行

```bash
# メッセージ分割機能のテストのみ
python -m pytest tests/test_notifier.py::TestSplitMessage -v

# Discord送信機能のテストのみ
python -m pytest tests/test_notifier.py::TestSendDiscordMessage -v
```

### 特定のテストを実行

```bash
# 例：短いメッセージが分割されないテストのみ
python -m pytest tests/test_notifier.py::TestSplitMessage::test_short_message_not_split -v
```

### テスト結果をカバレッジ付きで実行

```bash
pip install pytest-cov
python -m pytest tests/test_notifier.py -v --cov=services/notifier
```

## テストの説明

### TestSplitMessage クラス

メッセージ分割機能のテスト：

| テスト                                   | 説明                                         |
| ---------------------------------------- | -------------------------------------------- |
| `test_short_message_not_split`           | 2000 文字未満のメッセージは分割されない      |
| `test_exact_limit_message`               | ちょうど 2000 文字のメッセージは分割されない |
| `test_over_limit_message`                | 2000 文字を超えるメッセージは分割される      |
| `test_multiline_message`                 | 複数行のメッセージは適切に分割される         |
| `test_single_very_long_line`             | 1 行が超長の場合は分割される                 |
| `test_custom_max_length`                 | カスタム最大文字数で分割される               |
| `test_empty_message`                     | 空のメッセージへの対応                       |
| `test_message_with_newlines_at_boundary` | 改行を含むメッセージが正確に分割される       |

### TestSendDiscordMessage クラス

Discord 送信機能のテスト（非同期）：

| テスト                                   | 説明                                       |
| ---------------------------------------- | ------------------------------------------ |
| `test_send_short_message_success`        | 短いメッセージが正常に送信される           |
| `test_send_long_message_split`           | 長いメッセージが複数回に分割して送信される |
| `test_send_message_with_custom_username` | カスタムユーザー名で送信される             |
| `test_send_message_failure`              | エラーステータスで False が返される        |
| `test_send_message_exception`            | 例外が発生した場合の処理                   |

## テスト実行例

```bash
$ python -m pytest tests/test_notifier.py -v

tests/test_notifier.py::TestSplitMessage::test_short_message_not_split PASSED
tests/test_notifier.py::TestSplitMessage::test_exact_limit_message PASSED
tests/test_notifier.py::TestSplitMessage::test_over_limit_message PASSED
tests/test_notifier.py::TestSplitMessage::test_multiline_message PASSED
tests/test_notifier.py::TestSplitMessage::test_single_very_long_line PASSED
tests/test_notifier.py::TestSplitMessage::test_custom_max_length PASSED
tests/test_notifier.py::TestSplitMessage::test_empty_message PASSED
tests/test_notifier.py::TestSplitMessage::test_message_with_newlines_at_boundary PASSED
tests/test_notifier.py::TestSendDiscordMessage::test_send_short_message_success PASSED
tests/test_notifier.py::TestSendDiscordMessage::test_send_long_message_split PASSED
tests/test_notifier.py::TestSendDiscordMessage::test_send_message_with_custom_username PASSED
tests/test_notifier.py::TestSendDiscordMessage::test_send_message_failure PASSED
tests/test_notifier.py::TestSendDiscordMessage::test_send_message_exception PASSED

============= 13 passed in 0.23s =============
```
