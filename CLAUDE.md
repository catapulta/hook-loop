# hook-loop

3D-printable adapter joining a PVC docking stick to a boat-hook shaft, replacing
the discontinued Docking Stick. See [README.md](README.md) for what the product
is and [docs/design.md](docs/design.md) for how the adapter is dimensioned.

## Tooling & Commands

- **build123d + YACV**: Parametric CAD modeling with build123d and interactive YACV viewer.
  - Setup: `uv sync --extra dev`
  - Test geometry: `uv run --extra dev pytest`
  - View model in YACV: `uv run --extra view python show.py <part>` (serves on <http://localhost:32323>)
  - Live-reloading viewer: `uv run --extra view python show.py <part> --watch`
  - Export STL: `uv run python show.py <part> --stl out/<part>.stl`

Start the `--watch` viewer in the background at the start of a CAD session, then
pause at each geometry change and ask for a look. A human read of the live model
beats an agent's read of a screenshot. Don't batch changes into one review.

See [docs/build123d.md](docs/build123d.md) for full CAD conventions, viewer
usage, and sectioning guidance.

## CAD Conventions

- One Python module per printed part; each module exposes a factory function returning a `build123d.Part`.
- Parametric measurements defined as formulas (`total_l = gear_h + boss_h`), no magic numbers.
- Interface dimensions defined in shared modules (`lib/pipe.py` holds the pipe spec and hook shaft diameter).
- All committed CAD models must compile clean, valid, and watertight.

## This part

- **Two measured inputs.** `HOOK_SHAFT_D` and `PIPE` in `lib/pipe.py` drive every
  other dimension. Fitting a different hook or pipe means changing those, not
  editing the part.
- **The saddle uses a sleeve-axis conical envelope.** Extrude the complete C and
  web, fillet the waist, then subtract mirrored triangular revolutions around
  the sleeve axis. The lower cone grows outward from the sleeve at 60 degrees;
  the upper cone retracts into it.
- **The web and lips share one cutter.** Separate lofts can leave the rectangular
  web proud of the circular lips. Tests measure the solid's sleeve-axis radius
  at both ends to guard the common envelope.
- **Tests measure the solid.** Geometry assertions section the built part rather
  than reading parameters back, so they catch modelling errors that leave the
  parameters correct.
- **No fastener.** Retention is elastic: the saddle throat is narrower than the
  shaft and grips by hoop tension.
- **Grip is solved, not chosen.** `TARGET_RELEASE_N` and the 10 mm complete-C
  hold are the inputs. `conical_saddle_for_force` solves wall thickness and
  total height together. Pre-equator lip slices contribute no retention;
  retaining slices are integrated as parallel springs.
- `uv run scripts/retention.py --sweep length|material|throat` explores the
  trade-offs without touching the CAD.
- `ROOT_COMPLIANCE` in `lib/retention.py` is the one uncalibrated constant left;
  the arc's own compliance is derived from the wrap angle. Ratios are
  trustworthy, absolute newtons are not, until someone measures a real pull-off.
- **A thicker saddle wall is a more brittle one.** The lips bend a fixed distance
  to admit the shaft, so stress rises with thickness. Thinning `saddle_wall`
  raises the safety factor and lengthens the solved saddle; don't "strengthen"
  the clip by thickening it.
- The straight-cantilever limit test in `tests/test_retention.py` guards the
  curved-beam derivation. If it fails, the moment arm is wrong -- don't loosen
  its tolerance.

## Notes

- `is_valid` is a property on build123d 0.11.1, not a method.
- Waist fillets are applied to the complete extrusion before the conical cuts.
- The socket mouth chamfer is selected by matching `socket_bore_d`, not by
  "smallest circle at Z=0": the rope bore is smaller and also lands at Z=0.
- The rope runs the full length of the stick. `rope_bore_d` is exactly `PIPE.id`
  so the adapter never becomes the narrowest point in the channel; anything
  undersize takes the rope's chafe by itself. Don't "clean up" that equality.
