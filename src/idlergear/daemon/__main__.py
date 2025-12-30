"""Entry point for running daemon as a module: python -m idlergear.daemon"""

import sys
from pathlib import Path

from idlergear.daemon.server import run_daemon


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m idlergear.daemon <idlergear_root>", file=sys.stderr)
        sys.exit(1)

    idlergear_root = Path(sys.argv[1])
    if not idlergear_root.exists():
        print(f"Error: Directory not found: {idlergear_root}", file=sys.stderr)
        sys.exit(1)

    run_daemon(idlergear_root)


if __name__ == "__main__":
    main()
