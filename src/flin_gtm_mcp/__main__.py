import argparse
import json
import sys

from . import __version__, auth


def main():
    parser = argparse.ArgumentParser(description="flin Google Tag Manager MCP (read-only)")
    parser.add_argument("command", nargs="?", choices=["serve", "login", "status"], default="serve")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    if args.command == "serve":
        from .server import mcp

        mcp.run(transport="stdio")
    else:
        try:
            result = auth.login() if args.command == "login" else auth.status()
        except auth.AuthError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from None
        print(json.dumps(result, indent=2))
        if not result.get("authenticated"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
