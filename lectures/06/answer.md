# 第6回 解答

## 演習

## 演習：MCPサーバーをエージェントから利用する

### STEP 1：ツール一覧の確認

通常エージェントとMCPエージェントのツール一覧を比較した。

通常エージェントでは、`search_materials`、`search_glossary`、`get_lecture_summary`、`save_learning_log`、`make_quiz`の5ツールが登録されていた。

一方、MCPエージェントでは、用語集サーバーから`glossary_search_glossary`が1つ公開されていた。

両者ともツール名、説明文、引数がモデルに渡されるが、MCPではサーバー名がツール名の接頭辞となる点が異なっていた。

### STEP 2：自作MCPサーバーの呼び出し

質問：

「AIE2026の講座の宿題にある『3レベル』とは何ですか？」

実行結果：

```text
[tool call] glossary_search_glossary({'query': '3レベル'})
[tool return] glossary_search_glossary -> [{"term": "宿題の3レベル", ...}]
[usage] 入力 715 tokens / 出力 143 tokens / モデル応答 2 回
```

回答では、基礎・実装・発展の3段階が説明された。

第3回ではPython関数を直接呼び出していたが、今回はMCPサーバーを経由して同じ検索機能を利用できた。

### STEP 3：公開fetch MCPサーバー

`app/mcp_servers.json`に以下のサーバーを追加した。

```json
"fetch": {
  "command": "uvx",
  "args": ["mcp-server-fetch==2026.11.11", "--no-readability-js"]
}
```

ツール一覧に`fetch_fetch`が追加されたことを確認した。

質問：

「https://modelcontextprotocol.io/ の冒頭を日本語で3行に要約して」

実行結果：

```text
[tool call] fetch_fetch({'url': 'https://modelcontextprotocol.io/'})
[tool return] fetch_fetch -> Contents of https://modelcontextprotocol.io/:
[usage] 入力 2,230 tokens / 出力 110 tokens / モデル応答 2 回
```

HTTPリダイレクト後にページの取得が成功し、MCPの概要を日本語で3行に要約できた。

### STEP 4：AWS Knowledge MCPサーバー

接続設定に以下を追加した。

```json
"aws": {
  "url": "https://knowledge-mcp.global.api.aws"
}
```

ツール一覧では、用語集1個、fetch1個、AWS5個の合計7ツールが確認できた。

質問：

「AWSのドキュメントを検索して、Amazon S3のバージョニングを2行で説明して」

実行結果：

```text
[tool call] aws_aws___search_documentation({'search_phrase': 'Amazon S3 バージョニング 概要', 'topics': ['general']})
[tool call] aws_aws___search_documentation({'topics': ['general'], 'search_phrase': 'Using versioning in S3 buckets'})
[usage] 入力 11,153 tokens / 出力 126 tokens / モデル応答 3 回
```

AWSのMCPサーバーを通じてドキュメントを検索し、S3のバージョニングによる複数バージョンの保持、誤操作からの保護、過去版の復元について回答できた。

### 考察

今回の演習を通じて、Python関数の直接登録、Codespaces内で起動するMCPサーバー、外部URLに接続するMCPサーバーの違いを確認できた。

特に、MCPでは接続先を設定するだけで、エージェント側のコードを変更せずに外部ツールを追加できる点が有用だと感じた。

一方、AWSのドキュメント検索では入力トークン数が11,153と多く、外部ツールの結果をモデルに渡す際のトークン消費にも注意が必要だと分かった。


## 宿題

<!-- 基礎・実装・発展のどれか1つに取り組めば完了です。 -->

- 取り組んだレベル：基礎 / 実装 / 発展
- やったこと：
- 結果：
- 気づき・疑問：
