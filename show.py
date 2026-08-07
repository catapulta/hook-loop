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
import sys
import threading
import time
import traceback
from pathlib import Path

from build123d import Part, export_stl

ROOT = Path(__file__).resolve().parent


def load_part(module_name: str) -> Part:
    """Import `<module_name>` and call its same-named factory function."""
    module = importlib.import_module(module_name)
    factory = getattr(module, module_name, None)
    if factory is None or not callable(factory):
        raise SystemExit(
            f"{module_name}.py must define a {module_name}() returning a Part"
        )
    return factory()


def watched_sources() -> list[Path]:
    """Project sources whose edits should rebuild the part."""
    return sorted(ROOT.glob("*.py")) + sorted((ROOT / "lib").glob("*.py"))


def source_stamp() -> dict[Path, float]:
    """Mtime per watched source; comparing two stamps detects any edit."""
    stamp = {}
    for path in watched_sources():
        try:
            stamp[path] = path.stat().st_mtime
        except OSError:
            pass  # Deleted mid-scan; a later scan picks up the settled state.
    return stamp


def purge_project_modules() -> None:
    """Drop this project's modules so the next import rebuilds them cold.

    Reloading only the part module would re-execute its body against a cached
    `lib.pipe`, silently re-showing the old geometry after a parameter edit.
    Dropping the whole graph sidesteps having to reload in dependency order.
    """
    for name in list(sys.modules):
        module = sys.modules[name]
        file = getattr(module, "__file__", None)
        if not file:
            continue
        try:
            relative = Path(file).resolve().relative_to(ROOT)
        except ValueError:
            continue  # Outside the project (stdlib and other site-packages).
        # The venv sits under ROOT, so a bare relative_to(ROOT) also matches
        # numpy and build123d. Re-importing an extension module raises
        # "cannot load module more than once per process", so keep to our own
        # sources; dependencies hold no part parameters and need no reload.
        if relative.parts[0] == ".venv":
            continue
        if name != "__main__":
            del sys.modules[name]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("part", help="module name, e.g. outer_gear")
    parser.add_argument("--stl", type=Path, help="export to this STL instead of showing")
    parser.add_argument("--tolerance", type=float, default=0.001)
    parser.add_argument("--angular-tolerance", type=float, default=0.05)
    parser.add_argument(
        "--watch",
        action="store_true",
        help="rebuild and re-show whenever a project source changes",
    )
    parser.add_argument(
        "--poll-interval", type=float, default=0.5, help="--watch poll period, seconds"
    )
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
        if not args.watch:
            threading.Event().wait()
        else:
            print(f"  watching {len(watched_sources())} sources")
            stamp = source_stamp()
            while True:
                time.sleep(args.poll_interval)
                current = source_stamp()
                if current == stamp:
                    continue
                stamp = current

                # Showing under the same name replaces the model in every
                # connected frontend, so the open tab updates without a reload.
                try:
                    purge_project_modules()
                    part = load_part(args.part)
                    server.show(part, names=[args.part])
                    print(
                        f"  rebuilt {args.part}: valid={part.is_valid} "
                        f"volume={part.volume:.3f} mm^3",
                        flush=True,
                    )
                except Exception:
                    # A syntax error mid-edit must not kill the server; the
                    # next save gets another chance.
                    print("  rebuild failed, keeping previous model:", flush=True)
                    traceback.print_exc()
    except KeyboardInterrupt:
        print("\n  stopping")
        server.stop()


if __name__ == "__main__":
    main()
