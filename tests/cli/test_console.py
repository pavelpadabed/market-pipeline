import pytest

from market_pipeline.cli.console import (
    display_message,
    prompt_user,
)


def test_display_message_writes_message_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    message = "No games found for your query"
    expected_output = f"{message}\n"
    display_message(message)

    captured = capsys.readouterr()

    assert captured.out == expected_output


def test_prompt_user_passes_prompt_to_input_and_returns_raw_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Select a game or 'q' to quit: "
    raw_response = " 2 "
    received_prompts: list[str] = []

    def fake_input(
        received_prompt: str,
    ) -> str:
        received_prompts.append(received_prompt)
        return raw_response

    monkeypatch.setattr("builtins.input", fake_input)

    result = prompt_user(prompt)

    assert result == raw_response
    assert received_prompts == [prompt]
