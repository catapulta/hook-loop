# hook-loop

A 3D-printable  mooring aid that lets one person drop a line over a dock cleat
from the deck, at arm's length plus a metre.

The tool is two pieces. A length of schedule-40 PVC pipe is the stick. A
printed **adapter** cements onto the end of that pipe and carries a C-shaped
saddle that clips sideways onto the shaft of an ordinary telescoping boat hook.

Reaching out, the stick rides alongside the hook and shares its reach. The
mooring line is carried in the stick's open end, dropped over the cleat, and
the stick is pulled straight back off the hook — leaving the line on the cleat.
Only the adapter is printed; the hook and the pipe are sourced.

## Parts

| Module | Printed | What it is |
| --- | --- | --- |
| `hook_adapter.py` | yes | Pipe socket + boat-hook saddle |
| `pvc_pipe.py` | no | The sourced pipe, modelled for fit-checking |

## Sizing it for your hook

Every dimension derives from two measurements in `lib/pipe.py`:

- `HOOK_SHAFT_D` — your boat hook's shaft diameter where the saddle clips on
  (default 25.4 mm / 1 inch; telescoping hooks run 25–32 mm on the butt section).
- `PIPE` — which schedule-40 pipe you're building the stick from
  (default 1/2", i.e. 21.34 mm OD).

Measure your hook, change those, re-export. Nothing else needs touching.

## Printing

Print it **standing on the socket mouth**, bore vertical. The sleeve and the
saddle both reach the bed, and the saddle's conical envelope grows outward from
the sleeve at a self-supporting slope, so every layer sits squarely on the one
beneath it — no supports needed.

That orientation is also the strong one. Both loads run *around* the part
rather than across it: the saddle grips by hoop tension as its lips spread over
the shaft, and the pipe levers against the saddle through the filleted waist.
Standing, those stresses are carried by continuous extrusions within each
layer. Printed lying down they would pull directly on the layer bonds, which
is where a printed part splits.

Suggested: PETG or ASA for UV and saltwater tolerance, 3+ perimeters, 40%+
infill. PLA will work for a season but creeps in sun and heat.

```bash
uv sync --extra dev
uv run --extra dev pytest                                   # geometry checks
uv run python show.py hook_adapter --stl out/hook_adapter.stl  # export for slicing
uv run --extra view python show.py hook_adapter --watch       # inspect and rebuild
```

Watch mode removes the conventional `out/<part>.stl` export whenever source
changes make it stale. Export again after the model is ready to slice.

## Assembly

1. Cut the PVC pipe to length — around 900 mm is a good starting point.
2. Deburr and dry-fit: the pipe should bottom out on the adapter's internal
   shoulder, which sets the insertion depth. The bore carries on through at the
   pipe's own inside diameter, so the assembled stick stays open end to end and
   the rope runs through without catching on the adapter.
3. Solvent-cement the joint. The socket bore carries 0.4 mm of clearance for
   the cement film, so it is a slip fit before gluing, not a press fit.
4. Clip the saddle over the hook shaft. It should take a deliberate push to
   seat and a deliberate pull to release.

See [docs/build123d.md](docs/build123d.md) for CAD conventions and viewer
usage, and [docs/design.md](docs/design.md) for how the adapter is dimensioned.
