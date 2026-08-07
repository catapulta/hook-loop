"""Explore how saddle geometry and filament choice trade off against grip.

    uv run scripts/retention.py
    uv run scripts/retention.py --material asa --length 25
    uv run scripts/retention.py --sweep length
    uv run scripts/retention.py --sweep material

Defaults come from the committed part, so a bare run reports what the model in
`hook_adapter.py` is actually predicted to do. Pass `--target` to ask the
reverse question: how long the saddle must be for a given release force.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hook_adapter as h
from lib.materials import MATERIAL, MATERIALS
from lib.retention import evaluate, length_for_force


def _row(label: str, r) -> str:
    flag = "" if r.is_safe else "  YIELDS"
    return (
        f"{label:>10}  {r.release_force:8.1f}  {r.settled_force:10.1f}"
        f"  {r.peak_stress:10.1f}  {r.safety_factor:5.2f}{flag}"
    )


HEADER = (
    f"{'':>10}  {'new (N)':>8}  {'settled(N)':>10}"
    f"  {'sigma(MPa)':>10}  {'SF':>5}"
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--material", default=MATERIAL.name.lower(),
                   choices=sorted(MATERIALS))
    p.add_argument("--length", type=float, default=h.effective_saddle_length,
                   help="stiffness-equivalent full-C length, mm")
    p.add_argument("--wall", type=float, default=h.saddle_wall)
    p.add_argument("--bore", type=float, default=h.saddle_bore_d)
    p.add_argument("--throat", type=float, default=h.throat_w,
                   help="throat width, mm (default: the part's own)")
    p.add_argument("--target", type=float,
                   help="solve for the length giving this release force, N")
    p.add_argument("--sweep", choices=("length", "material", "throat"))
    args = p.parse_args()

    material = MATERIALS[args.material]
    kw = dict(wall=args.wall, bore_d=args.bore, throat_w=args.throat)

    print(f"{material.name}  E={material.e_modulus:.0f} MPa  "
          f"yield={material.yield_stress:.0f} MPa  "
          f"grip retained={material.set_factor:.0%}")
    print(f"bore={args.bore:.2f}  throat={args.throat:.2f} "
          f"({args.throat / args.bore:.2f}x)  wall={args.wall:.2f}  "
          f"lip spread={(args.bore - args.throat) / 2:.2f} mm each")
    if material.notes:
        print(f"  {material.notes}")
    print()

    if args.target:
        solved = length_for_force(material, target_force=args.target, **kw)
        print(f"length for {args.target:.0f} N release: {solved:.1f} mm")
        print(HEADER)
        print(_row(f"{solved:.1f}mm", evaluate(material, length=solved, **kw)))
        return

    if args.sweep == "length":
        print(HEADER)
        for length in (10, 15, 17.5, 20, 25, 30, 35):
            mark = (
                "  <- part"
                if abs(length - h.effective_saddle_length) < 0.75 else ""
            )
            print(_row(f"{length}mm", evaluate(material, length=length, **kw))
                  + mark)
    elif args.sweep == "material":
        print(f"at length={args.length:.1f} mm")
        print(HEADER)
        for key in sorted(MATERIALS):
            m = MATERIALS[key]
            print(_row(m.name, evaluate(m, length=args.length, **kw)))
    elif args.sweep == "throat":
        print(f"at length={args.length:.1f} mm")
        print(HEADER)
        for ratio in (0.70, 0.75, 0.80, 0.85, 0.90):
            throat = args.bore * ratio
            r = evaluate(material, length=args.length, wall=args.wall,
                         bore_d=args.bore, throat_w=throat)
            print(_row(f"{ratio:.2f}x", r))
    else:
        print(HEADER)
        print(_row(f"{args.length:.1f}mm",
                   evaluate(material, length=args.length, **kw)))


if __name__ == "__main__":
    main()
