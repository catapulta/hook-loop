"""Interactive viewer / STL exporter for the build123d parts.

    uv run --extra view python show.py outer_gear          # open in YACV
    uv run python show.py outer_gear --stl out/og.stl      # export only

Importing `yacv_server` starts its HTTP server and blocks at exit until a
frontend connects, so the import is deferred into the show path: an `--stl` run
never pulls it in. The viewer runs until Ctrl-C rather than shutting down after
the first frontend fetch.
"""

import argparse
import importlib
import os
import threading
from pathlib import Path

from build123d import Part, export_stl


def load_part(module_name: str) -> Part:
    """Import `<module_name>` and call its same-named factory function."""
    module = importlib.import_module(module_name)
    factory = getattr(module, module_name, None)
    if factory is None or not callable(factory):
        raise SystemExit(
            f"{module_name}.py must define a {module_name}() returning a Part"
        )
    return factory()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("part", help="module name, e.g. outer_gear")
    parser.add_argument("--stl", type=Path, help="export to this STL instead of showing")
    parser.add_argument("--tolerance", type=float, default=0.001)
    parser.add_argument("--angular-tolerance", type=float, default=0.05)
    args = parser.parse_args()

    part = load_part(args.part)
    print(f"{args.part}: valid={part.is_valid} volume={part.volume:.3f} mm^3")
    bb = part.bounding_box()
    print(f"  bbox {tuple(round(v, 3) for v in bb.min)} .. "
          f"{tuple(round(v, 3) for v in bb.max)}")

    if args.stl:
        args.stl.parent.mkdir(parents=True, exist_ok=True)
        export_stl(
            part,
            str(args.stl),
            tolerance=args.tolerance,
            angular_tolerance=args.angular_tolerance,
        )
        print(f"  wrote {args.stl}")
        return

    # Import starts yacv_server's module-level singleton and binds the port;
    # constructing a second YACV() would lose that bind race and serve nothing.
    # Show onto the singleton, then block: left to itself the process would exit
    # once a frontend had fetched the model, closing the viewer mid-review.
    from yacv_server import yacv as server

    server.show(part, names=[args.part])

    host = os.getenv("YACV_HOST", "localhost")
    port = os.getenv("YACV_PORT", "32323")
    print(f"  serving on http://{host}:{port} (Ctrl-C to stop)")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n  stopping")
        server.stop()


if __name__ == "__main__":
    main()
