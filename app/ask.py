"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --chat     # 会話履歴を保って対話する

単発モードではツールも会話履歴も持たない「素の」呼び出し。
対話モードでは Google GenAI SDK の Chat を使い、同じ会話の履歴を保つ。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse
import csv
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
import time

from google import genai
from google.genai import errors
from google.genai.types import GenerateContentResponse, HttpOptions, HttpRetryOptions

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"
BENCHMARK_PATH = Path("results/benchmark.csv")
BENCHMARK_FIELDS = (
    "timestamp_utc",
    "model",
    "question",
    "response_time_seconds",
    "input_tokens",
    "output_tokens",
    "status",
    "http_error_code",
)


def _print_usage(response: GenerateContentResponse) -> None:
    usage = response.usage_metadata
    if usage is not None:
        print(
            f"[tokens] input={usage.prompt_token_count}, "
            f"output={usage.candidates_token_count}"
        )


def _create_client(benchmark: bool) -> genai.Client:
    if benchmark:
        return genai.Client(
            api_key=get_api_key(),
            http_options=HttpOptions(
                retry_options=HttpRetryOptions(attempts=1)
            ),
        )
    return genai.Client(api_key=get_api_key())


def _append_benchmark(
    timestamp: str,
    question: str,
    elapsed: float,
    response: GenerateContentResponse | None,
    error_code: int | None = None,
) -> None:
    BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not BENCHMARK_PATH.exists() or BENCHMARK_PATH.stat().st_size == 0
    usage = response.usage_metadata if response is not None else None

    with BENCHMARK_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=BENCHMARK_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": timestamp,
                "model": MODEL,
                "question": question,
                "response_time_seconds": f"{elapsed:.6f}",
                "input_tokens": usage.prompt_token_count if usage else "",
                "output_tokens": usage.candidates_token_count if usage else "",
                "status": "failure" if error_code is not None else "success",
                "http_error_code": error_code if error_code is not None else "",
            }
        )


def _send_with_metrics(
    question: str,
    send: Callable[[], GenerateContentResponse],
    benchmark: bool,
) -> GenerateContentResponse:
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started = time.perf_counter()
    try:
        response = send()
    except errors.APIError as error:
        elapsed = time.perf_counter() - started
        print(f"[time] {elapsed:.3f}s")
        if benchmark:
            _append_benchmark(timestamp, question, elapsed, None, error.code)
        raise

    elapsed = time.perf_counter() - started
    print(f"[time] {elapsed:.3f}s")
    _print_usage(response)
    if benchmark:
        _append_benchmark(timestamp, question, elapsed, response)
    return response


def ask(question: str, benchmark: bool = False) -> str:
    client = _create_client(benchmark)
    response = _send_with_metrics(
        question,
        lambda: client.models.generate_content(model=MODEL, contents=question),
        benchmark,
    )
    return response.text


def run_chat(benchmark: bool = False) -> None:
    client = _create_client(benchmark)
    chat = client.chats.create(model=MODEL)

    print("対話を開始します。終了するには exit または quit を入力してください。")
    while True:
        try:
            question = input("[質問] ").strip()
        except EOFError:
            print()
            break

        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        response = _send_with_metrics(
            question,
            lambda: chat.send_message(question),
            benchmark,
        )
        print(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--chat", action="store_true", help="会話履歴を保って対話する")
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="計測結果を results/benchmark.csv に追記する",
    )
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    try:
        if args.chat:
            run_chat(benchmark=args.benchmark)
        else:
            question = DEFAULT_QUESTION if args.question is None else args.question
            print(f"[質問] {question}\n")
            print(ask(question, benchmark=args.benchmark))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
