"""
Entry point for python -m squelch
"""

import sys


def main():
    # Check for --cli flag to use old CLI
    if "--cli" in sys.argv:
        from .cli import run
        run()
    else:
        from .tui import SquelchApp
        app = SquelchApp()
        app.run()


if __name__ == "__main__":
    main()