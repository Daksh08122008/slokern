"""
Purpose: CLI module runner for `python -m slokern.cli`.
Owner: Rajdeep
"""

import sys

from slokern.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
