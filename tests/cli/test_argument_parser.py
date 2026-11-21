from pathlib import Path

import pytest

from market_pipeline.cli.argument_parser import parse_cli_arguments
from market_pipeline.cli.models import CliArguments


def test_parse_cli_arguments_returns_normalized_query_and_default_output_dir(
) -> None:
    cli_arguments = parse_cli_arguments(["--query", " The Witcher 3 "])

    assert isinstance(cli_arguments, CliArguments)
    assert cli_arguments.query == "The Witcher 3"
    assert cli_arguments.output_dir == Path("outputs")


def test_parse_cli_arguments_returns_user_provided_output_dir() -> None:
    cli_arguments = parse_cli_arguments(
        [
            "--query",
            "The Witcher 3",
            "--output-dir",
            "reports/custom",
        ]
    )

    assert cli_arguments.output_dir == Path("reports/custom")


def test_parse_cli_arguments_rejects_blank_query() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_cli_arguments(["--query", "   "])

    assert exc_info.value.code == 2


def test_parse_cli_arguments_rejects_missing_query() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_cli_arguments([])

    assert exc_info.value.code == 2


def test_parse_cli_arguments_rejects_missing_query_value() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_cli_arguments(["--query"])

    assert exc_info.value.code == 2


def test_parse_cli_arguments_rejects_positional_query() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_cli_arguments(["The Witcher 3"])

    assert exc_info.value.code == 2


def test_parse_cli_arguments_rejects_missing_output_dir_value() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_cli_arguments(["--query", "The Witcher 3", "--output-dir"])

    assert exc_info.value.code == 2
