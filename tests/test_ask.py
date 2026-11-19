import csv
from types import SimpleNamespace
from unittest.mock import Mock, call

from app import ask as ask_module
from app.config import MODEL
from google.genai import errors


def test_chat_keeps_conversation_and_benchmarks_each_turn(
    monkeypatch, capsys, tmp_path
):
    responses = [
        SimpleNamespace(
            text="最初の回答",
            usage_metadata=SimpleNamespace(
                prompt_token_count=2, candidates_token_count=3
            ),
        ),
        SimpleNamespace(
            text="続きの回答",
            usage_metadata=SimpleNamespace(
                prompt_token_count=5, candidates_token_count=4
            ),
        ),
    ]
    chat = Mock()
    chat.send_message.side_effect = responses
    client = Mock()
    client.chats.create.return_value = chat
    client_factory = Mock(return_value=client)
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask_module.genai, "Client", client_factory)
    monkeypatch.setattr(ask_module, "BENCHMARK_PATH", tmp_path / "benchmark.csv")
    times = iter([10.0, 10.25, 20.0, 20.75])
    monkeypatch.setattr(ask_module.time, "perf_counter", lambda: next(times))
    questions = iter(["最初の質問", "続きの質問", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(questions))

    ask_module.run_chat(benchmark=True)

    client.chats.create.assert_called_once_with(model=MODEL)
    assert client_factory.call_args.kwargs["http_options"].retry_options.attempts == 1
    assert chat.send_message.call_args_list == [
        call("最初の質問"),
        call("続きの質問"),
    ]
    output = capsys.readouterr().out
    assert "最初の回答" in output
    assert "続きの回答" in output
    assert "[tokens] input=2, output=3" in output
    assert "[tokens] input=5, output=4" in output
    assert "test-key" not in output
    with ask_module.BENCHMARK_PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert [row["question"] for row in rows] == ["最初の質問", "続きの質問"]
    assert [row["response_time_seconds"] for row in rows] == [
        "0.250000",
        "0.750000",
    ]


def test_single_question_benchmark_appends_success_row(
    monkeypatch, capsys, tmp_path
):
    response = SimpleNamespace(
        text="回答",
        usage_metadata=SimpleNamespace(
            prompt_token_count=7, candidates_token_count=8
        ),
    )
    client = Mock()
    client.models.generate_content.side_effect = [response, response]
    client_factory = Mock(return_value=client)
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask_module.genai, "Client", client_factory)
    monkeypatch.setattr(ask_module, "BENCHMARK_PATH", tmp_path / "benchmark.csv")
    times = iter([10.0, 11.23456, 12.0, 12.1])
    monkeypatch.setattr(ask_module.time, "perf_counter", lambda: next(times))

    assert ask_module.ask("LoRAとは？", benchmark=True) == "回答"
    assert ask_module.ask("LoRAを簡単に", benchmark=True) == "回答"

    assert client.models.generate_content.call_args_list == [
        call(model=MODEL, contents="LoRAとは？"),
        call(model=MODEL, contents="LoRAを簡単に"),
    ]
    options = client_factory.call_args.kwargs["http_options"]
    assert options.retry_options.attempts == 1
    output = capsys.readouterr().out
    assert "[time] 1.235s" in output
    assert "[tokens] input=7, output=8" in output
    assert "test-key" not in output

    with ask_module.BENCHMARK_PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    assert rows[0]["model"] == MODEL
    assert rows[0]["question"] == "LoRAとは？"
    assert rows[0]["response_time_seconds"] == "1.234560"
    assert rows[0]["input_tokens"] == "7"
    assert rows[0]["output_tokens"] == "8"
    assert rows[0]["status"] == "success"
    assert rows[0]["http_error_code"] == ""
    assert rows[0]["timestamp_utc"].endswith("Z")
    assert rows[1]["question"] == "LoRAを簡単に"
    assert rows[1]["response_time_seconds"] == "0.100000"


def test_api_error_is_recorded_without_exception_message(
    monkeypatch, capsys, tmp_path
):
    client = Mock()
    client.models.generate_content.side_effect = errors.APIError(
        429, {"error": {"message": "private response detail"}}
    )
    client_factory = Mock(return_value=client)
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask_module.genai, "Client", client_factory)
    monkeypatch.setattr(ask_module, "BENCHMARK_PATH", tmp_path / "benchmark.csv")
    times = iter([20.0, 20.5])
    monkeypatch.setattr(ask_module.time, "perf_counter", lambda: next(times))

    try:
        ask_module.ask("質問", benchmark=True)
    except errors.APIError:
        pass
    else:
        raise AssertionError("APIError should be propagated")

    output = capsys.readouterr().out
    assert "[time] 0.500s" in output
    assert "private response detail" not in output
    assert "test-key" not in output
    with ask_module.BENCHMARK_PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]["status"] == "failure"
    assert rows[0]["http_error_code"] == "429"
    assert rows[0]["input_tokens"] == ""
    assert rows[0]["output_tokens"] == ""
    assert "private response detail" not in str(rows)
