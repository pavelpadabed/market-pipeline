import argparse
from pathlib import Path

from market_pipeline.cli.models import CliArguments


def _parse_non_blank_query(raw_query: str) -> str:
    stripped_query = raw_query.strip()
    if not stripped_query:
        raise argparse.ArgumentTypeError("Query must not be blank")
    return stripped_query


def parse_cli_arguments(args: list[str]) -> CliArguments:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--query",
        type=_parse_non_blank_query,
        required=True,
        help="Game title to search for",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory where the report will be saved",
    )

    parsed_args = parser.parse_args(args)

    return CliArguments(
        query=parsed_args.query,
        output_dir=parsed_args.output_dir,
    )
