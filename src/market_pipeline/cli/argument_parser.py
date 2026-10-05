import argparse


def _parse_non_blank_query(raw_query: str) -> str:
    stripped_query = raw_query.strip()
    if not stripped_query:
        raise argparse.ArgumentTypeError("Query must not be blank")
    return stripped_query


def parse_query(args: list[str]) -> str:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--query",
        type=_parse_non_blank_query,
        required=True,
        help="Game title to search for",
    )

    parsed_args = parser.parse_args(args)

    return parsed_args.query
