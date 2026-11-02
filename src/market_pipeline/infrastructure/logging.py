import logging
import logging.handlers
from pathlib import Path


def configure_logging(path: Path) -> None:
    logger = logging.getLogger("market_pipeline")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handlers = logger.handlers
    if len(handlers) > 1:
        raise RuntimeError(
            "Logging configuration contains multiple handlers."
        )
    for handler in handlers:
        if not isinstance(handler, logging.handlers.RotatingFileHandler):
            raise RuntimeError(
                "Logging is already configured with an unsupported handler."
            )
        configured_path = Path(handler.baseFilename).resolve()
        requested_path = path.resolve()
        if configured_path != requested_path:
            raise RuntimeError(
                "Logging is already configured for a different file path."
            )
        return

    handler = logging.handlers.RotatingFileHandler(
        filename=path,
        mode="a",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
        delay=False,
    )

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
