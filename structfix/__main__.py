"""Executable entrypoint for python -m structfix."""

import sys
from structfix.cli import main

if __name__ == "__main__":
    sys.exit(main())
