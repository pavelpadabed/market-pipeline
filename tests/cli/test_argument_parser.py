import pytest

from market_pipeline.cli.argument_parser import parse_query


def test_parse_query_returns_stripped_query() -> None:
    query = parse_query(["--query", " The Witcher 3 "])

    assert query == "The Witcher 3"


def test_parse_query_rejects_blank_query() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_query(["--query", "   "])

    assert exc_info.value.code == 2


def test_parse_query_rejects_missing_query() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_query([])

    assert exc_info.value.code == 2


def test_parse_query_rejects_missing_query_value() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_query(["--query"])

    assert exc_info.value.code == 2


def test_parse_query_rejects_positional_query() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_query(["The Witcher 3"])

    assert exc_info.value.code == 2
