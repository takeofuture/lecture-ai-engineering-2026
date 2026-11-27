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

### 宿題1：基礎 — MCPサーバーへの講義要約ツールの追加

#### 目的

MCPサーバーに新しいツールを公開した際、エージェント側のコードや接続設定を変更せずに、そのツールを利用できることを確認する。

#### 実装内容

`app/mcp_server.py`に次の1行を追加した。

```python id="yjm6ni"
server.tool()(tools.get_lecture_summary)
```

これにより、第3回で使用した講義要約関数をMCPのツールとして公開した。

`app/mcp_agent.py`および`app/mcp_servers.json`は変更していない。

#### 動作確認

`uv run python -m app.mcp_agent --list-tools`を実行したところ、新たに次のツールが表示された。

```text id="fd4fk3"
[glossary_get_lecture_summary]
引数: {"lecture": {"title": "Lecture", "type": "integer"}}
```

MCPエージェントが認識するツールの総数は7個から8個に増えた。

次に、以下の質問を実行した。

```bash id="zfn97m"
uv run python -m app.mcp_agent --trace \
  "第2回では何を学びますか？"
```

トレース結果：

```text id="hd2hzu"
[tool call] glossary_get_lecture_summary({'lecture': 2})
[tool return] glossary_get_lecture_summary -> # 第2回 ファインチューニングとLoRA
[usage] 入力 5,942 tokens / 出力 310 tokens / モデル応答 2 回
```

回答では、事前学習とファインチューニング、SFT、PEFT・LoRA、QLoRA、Google Colabでの演習について説明された。

さらに、`uv run pytest -q`を実行し、24件すべてのテストが合格した。

#### 考察

今回の実装では、MCPサーバー側のツール登録を1行追加するだけで、既存のエージェントから新しいツールを利用できた。

エージェントは起動時にMCPサーバーから公開ツールの一覧を取得するため、ツールの追加ごとにエージェントのコードを修正する必要がない。

この仕組みは、複数のアプリケーションから共通の機能を利用したい場合や、サーバー側で機能を追加・管理する場合に有効だと考えた。

一方、今回の実行では入力トークン数が5,942となった。複数のMCPサーバーを接続するとツールの定義情報も増えるため、必要なツールだけを公開することが重要だと感じた。

**結論として、サーバー側の変更だけでMCPエージェントに新しい機能を追加できることを確認した。**

### 宿題2：実装 — クイズ生成ツールのMCP公開とエラー処理

#### 目的

第3回で作成した`make_quiz`をMCPツールとして公開し、正常な講義回と存在しない講義回を指定した場合の動作を比較する。また、エラー情報がMCP経由でLLMに正しく伝わるか検証する。

#### 実装内容

`app/mcp_server.py`に次の登録処理を追加した。

```python
server.tool()(tools.make_quiz)
```

これにより、既存のクイズ生成関数を`glossary_make_quiz`として公開した。

さらに、`app/tools.py`の`make_quiz`において、該当する講義回の用語が見つからない場合、以下の情報をJSON形式で返すよう改善した。

- `error`：クイズを作成できないこと
- `reason`：指定した回の用語が登録されていない理由
- `available_lectures`：利用可能な講義回
- `suggestion`：再入力の案内

#### 検証1：Pythonからの直接呼び出し

`make_quiz(2)`では、「量子化」の意味を問う問題と正解が返された。

`make_quiz(99)`では、次のJSONが返された。

```json
{
  "error": "第99回のクイズは作成できません。",
  "reason": "指定した回の用語が用語集に登録されていません。",
  "available_lectures": [1, 2, 3, 4, 6],
  "suggestion": "利用可能な講義回を指定して、もう一度質問してください。"
}
```

正常系・異常系のアサーションは両方成功した。また、`uv run pytest -q`では24件すべてのテストが合格した。

#### 検証2：MCP経由の正常系

次のコマンドを実行した。

```bash
uv run python -m app.mcp_agent --trace \
  "第2回の用語集からクイズを1問作って"
```

トレース：

```text
[tool call] glossary_make_quiz({'lecture': 2})
[tool return] glossary_make_quiz -> {"question": "「QLoRA」の意味は？", ...}
[usage] 入力 5,731 tokens / 出力 84 tokens / モデル応答 2 回
```

MCPツールが正常に呼び出され、GeminiはQLoRAに関する確認問題を提示した。

#### 検証3：MCP経由の異常系

最初に「第99回のクイズを作って」と質問したところ、GeminiはMCPツールを呼び出さず、第99回は存在しないと直接回答した。

このとき、トレースに`glossary_make_quiz`の呼び出しは記録されず、モデル応答は1回だった。

次に、`glossary_make_quiz`を明示的に呼び出し、`lecture=99`を渡すよう指示した。

```text
[tool call] glossary_make_quiz({'lecture': 99})
[tool return] glossary_make_quiz -> {"error": "第99回のクイズは作成できません。", ...}
[usage] 入力 5,797 tokens / 出力 110 tokens / モデル応答 2 回
```

この場合はMCPツールが実行され、Geminiは`error`、`reason`、`available_lectures`、`suggestion`を含むJSONを正しく出力した。

#### 考察

今回の検証から、MCPサーバーがツールを公開していても、LLMが必ずそのツールを呼び出すわけではないことが分かった。

通常の質問では、Geminiはツールを使用せずに回答した。一方、ツール名と引数を明示した場合は、実際にMCPを経由してエラー情報を取得した。

また、エラー発生時に単なる文字列ではなく、理由や利用可能な選択肢を構造化して返すことで、LLMが次の操作を案内しやすくなると考えられる。

実運用では、ツールの説明文やプロンプトを工夫し、必要な場面でツールが選択されるようにすることも重要だと感じた。

**結論として、既存のPython関数をMCPツールとして再利用し、正常系と異常系の両方で適切な情報を返せることを確認した。**

