import logging
import logging.handlers
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from market_pipeline.infrastructure.logging import configure_logging


@pytest.fixture(autouse=True)
def isolate_market_pipeline_logger() -> Iterator[None]:
    logger = logging.getLogger("market_pipeline")
    original_propagate = logger.propagate
    original_level = logger.level
    original_handlers = logger.handlers.copy()

    for handler in original_handlers:
        logger.removeHandler(handler)

    logger.setLevel(logging.NOTSET)
    logger.propagate = True

    yield

    for handler in logger.handlers.copy():
        logger.removeHandler(handler)
        handler.close()

    for handler in original_handlers:
        logger.addHandler(handler)

    logger.setLevel(original_level)
    logger.propagate = original_propagate


def test_configure_logging_writes_child_logger_info_message_to_file(tmp_path: Path) -> None:
    file_path = tmp_path / "market-pipeline.log"
    child_logger = logging.getLogger("market_pipeline.test")
    expected_message = "Pipeline started"

    configure_logging(file_path)
    child_logger.info(expected_message)

    actual_log = file_path.read_text(encoding="utf-8")

    assert expected_message in actual_log


def test_configure_logging_raises_runtime_error_for_different_path(tmp_path: Path) -> None:
    first_path = tmp_path / "market-pipeline.log"
    second_path = tmp_path / "different-market-pipeline.log"

    configure_logging(first_path)

    with pytest.raises(
        RuntimeError,
        match="already configured for a different file path",
    ):
        configure_logging(second_path)


def test_configure_logging_does_not_duplicate_message_for_same_path(tmp_path: Path) -> None:
    file_path = tmp_path / "market-pipeline.log"
    child_logger = logging.getLogger("market_pipeline.test")
    expected_message = "Pipeline started"

    configure_logging(file_path)
    configure_logging(file_path)
    child_logger.info(expected_message)

    actual_log = file_path.read_text(encoding="utf-8")

    actual_message_count = actual_log.count(expected_message)

    assert actual_message_count == 1


def test_configure_logging_raises_runtime_error_for_existing_unsupported_handler(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "market-pipeline.log"
    logger = logging.getLogger("market_pipeline")
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)

    with pytest.raises(
        RuntimeError,
        match="already configured with an unsupported handler",
    ):
        configure_logging(file_path)


def test_configure_logging_raises_runtime_error_for_multiple_handlers(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "market-pipeline.log"
    logger = logging.getLogger("market_pipeline")

    configure_logging(file_path)
    second_handler = logging.handlers.RotatingFileHandler(filename=file_path)
    logger.addHandler(second_handler)

    with pytest.raises(
        RuntimeError,
        match="configuration contains multiple handlers",
    ):
        configure_logging(file_path)


def test_configure_logging_writes_info_record_in_expected_format(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "market-pipeline.log"
    child_logger = logging.getLogger("market_pipeline.test")
    expected_message = "Pipeline started"
    expected_timestamp_format = "%Y-%m-%dT%H:%M:%S%z"

    configure_logging(file_path)
    child_logger.info(expected_message)

    actual_log = file_path.read_text(encoding="utf-8")

    actual_records = actual_log.splitlines()

    assert len(actual_records) == 1

    actual_record = actual_records[0]

    timestamp, level, logger_name, message = actual_record.split(" - ", maxsplit=3)

    assert level == "INFO"
    assert logger_name == "market_pipeline.test"
    assert message == expected_message

    parsed_timestamp = datetime.strptime(timestamp, expected_timestamp_format)
    assert parsed_timestamp.strftime(expected_timestamp_format) == timestamp


def test_configure_logging_does_not_write_child_logger_debug_message_to_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "market-pipeline.log"
    child_logger = logging.getLogger("market_pipeline.test")
    debug_message = "Pipeline started in debug mode"

    configure_logging(file_path)
    child_logger.debug(debug_message)

    actual_log = file_path.read_text(encoding="utf-8")

    assert actual_log == ""


def test_configure_logging_disables_propagation_to_root_logger(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "market-pipeline.log"
    logger = logging.getLogger("market_pipeline")

    configure_logging(file_path)

    assert logger.propagate is False


def test_configure_logging_raises_when_parent_directory_does_not_exist(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "missing directory" / "market-pipeline.log"

    with pytest.raises(FileNotFoundError):
        configure_logging(file_path)
