from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from generate_synthetic import generate_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic company artifact corpus.")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--reference-date", type=date.fromisoformat, default=date(2026, 5, 13))
    parser.add_argument("--clean", action="store_true", help="Remove the output directory before generation.")
    args = parser.parse_args()

    manifest = generate_corpus(args.output, args.reference_date, clean=args.clean)
    print(
        f"generated synthetic corpus accounts={len(manifest['accounts'])} "
        f"output={args.output} reference_date={args.reference_date.isoformat()}"
    )


if __name__ == "__main__":
    main()
