"""Paksward entry point.

    python3 main.py                opens Paksward in your browser
    python3 main.py --no-browser   prints the private link instead
"""
import argparse
import os
import sys
import webbrowser

# A packaged app started by double-click has no terminal; printing to a missing stream would crash.
for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, "w"))


def run_web(port, open_browser):
    from paksward import config, storage
    from paksward.api import Api
    from paksward.server import PakswardServer

    storage.ensure_dirs()
    try:
        api = Api()
    except ValueError:
        print(f"\nPaksward could not read {config.USERS_FILE}.\n"
              "The file looks damaged. Nothing was changed. Restore it from a backup copy, or move it\n"
              "aside and ask for help before creating any new account, because a new account would\n"
              "replace the damaged list.\n", file=sys.stderr)
        return 1

    server = PakswardServer(api, port=port)
    print("\nPaksward is running. It is only reachable from this computer.")
    print(f"\n  Open this link if your browser does not open by itself:\n  {server.url}\n")
    print("Keep this terminal open while you use Paksward. Press Ctrl+C here to quit.\n")
    if open_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nLocking the vault and quitting.")
    finally:
        api.lock()
        server.server_close()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Paksward password manager")
    ap.add_argument("--no-browser", action="store_true", help="print the link but do not open a browser")
    ap.add_argument("--port", type=int, default=0, help="port to listen on (default: any free port)")
    args = ap.parse_args(argv)
    return run_web(args.port, not args.no_browser)


if __name__ == "__main__":
    sys.exit(main())
