# build123d CAD Guidance

Parametric build123d sources and guidelines copied from `@../senda/hardware`.

## Tooling & Commands

```bash
uv sync --extra dev                                  # install dependencies
uv run --extra dev pytest                            # run geometry tests
uv run python show.py <part> --stl out/<part>.stl    # export STL
uv run --extra view python show.py <part>            # launch interactive YACV viewer
```

`show.py <module>` imports `<module>.py` and calls its same-named factory function, which returns a `build123d.Part`.
Watch mode removes `out/<module>.stl` whenever a watched source changes, so the
export directory cannot silently retain an obsolete printable model.

### YACV Viewer

The viewer serves on <http://localhost:32323> until Ctrl-C. Both side panels start collapsed — open **Tools** (right edge) to reach:

- **Selection** — pick faces, edges, and vertices with a mode dropdown (`Any (S)`, `(F)aces`, edge/vertex modes; key shortcut in parens). The heading shows selection count (e.g. `0F 1E 0V`). Selecting geometry dimensions it in 3D view. Selection requires this panel to be open.
- **Models** (left edge) — per-model toggles for face, edge, and vertex display.
- **Sandbox** — in-browser Pyodide Python playground. Local served page blocks external CDN loading; it is a scratch REPL rather than a live code view.

## Conventions

- **Module per part**: One Python module per printed body with a header docstring describing the part and exposing a single factory function returning a `Part`.
- **Parametric dimensions**: Measured values defined as named parameters with relationships expressed as formulas (`total_l = gear_h + boss_h`), avoiding magic numbers.
- **Involute gears**: Gear profiles are parametrically generated via `py_gearworks` (NURBS curves for exact tooth profiles, root fillets, undercut, backlash, profile shift), never hard-coded point lists.
- **Shared stack datums**: Interface dimensions and global datums live in shared library files (e.g., `lib/stack.py`); parts derive from shared datums.
- **Validation**: Committed parts must compile clean, valid, and watertight.
- **Repository hygiene**: Keep temporary STLs, renders, and scratch scripts out of the git repo.

## CAD & build123d Technical Behaviors

- **Gear Clocking**: `py_gearworks` clocks a tooth centered on `+X`. Parts requiring a tooth gap on a given axis apply `tooth_gap_angle(z)` offset (e.g., `90 + tooth_gap_angle(teeth)`).
- **Gear Bounding Boxes**: A clocked gear's bounding box does **not** measure tip-to-tip since `±X` extremes land in tooth gaps. Measure tip radius on a section instead.
- **Sectioning & Bores**: `section()` is a free function taking `(part, plane)`, not a `Part` method. Section vertices are arc endpoints, so measuring a bore's diameter from vertices understates it; measure the inner wire's bounding box instead.
- **YACV Server Singleton**: `import yacv_server` starts a module-level singleton on port 32323. Constructing custom `YACV()` instances loses the bind race. `show.py` uses the singleton and blocks to keep the viewer alive. Set `YACV_DISABLE_SERVER=1` to import without starting the server (preventing scripts from hanging at exit).
- **Re-showing Replaces**: `show()` under a name already displayed replaces that model in every connected frontend, so a rebuild reaches an open tab with no reload. This is what `--watch` relies on.
- **Reload Scope**: `--watch` drops the project's own modules from `sys.modules` so the next import rebuilds them cold. Reloading only the part module would re-execute it against a cached `lib.pipe` and silently re-show the old geometry after a parameter edit. The purge must exclude `.venv`, which lives under the repo root: re-importing a dependency's C extension (numpy, via build123d) raises `ImportError: cannot load module more than once per process`.
