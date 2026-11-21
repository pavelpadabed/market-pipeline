from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CliArguments:
    query: str
    output_dir: Path
