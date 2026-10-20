from types import SimpleNamespace
from unittest.mock import Mock, call

from app import ask as ask_module
from app.config import MODEL


def test_chat_keeps_conversation_in_one_session(monkeypatch, capsys):
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
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask_module.genai, "Client", Mock(return_value=client))
    questions = iter(["最初の質問", "続きの質問", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(questions))

    ask_module.run_chat()

    client.chats.create.assert_called_once_with(model=MODEL)
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
