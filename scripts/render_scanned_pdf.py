from __future__ import annotations

import argparse
from pathlib import Path

from generate_synthetic.render_scanned import render_scanned_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a clean PDF as a scanned-looking image PDF.")
    parser.add_argument("source_pdf", type=Path)
    parser.add_argument("output_pdf", type=Path)
    args = parser.parse_args()
    render_scanned_pdf(args.source_pdf, args.output_pdf)
    print(f"rendered scanned_pdf={args.output_pdf}")


if __name__ == "__main__":
    main()
