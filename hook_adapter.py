"""Printed adapter joining a PVC docking stick to a boat-hook shaft.

Replaces the head of the discontinued Docking Stick: a sleeve that solvent
cements onto the end of a PVC pipe, carrying alongside it a C-shaped saddle
that clips over the boat hook's shaft. Reaching out with the hook, the stick
rides along beside it; a mooring line is dropped over a cleat and the stick
pulls off the hook, leaving the line behind.

The complete saddle is extruded alongside the sleeve and trimmed at both ends
by conical cutters revolved around the sleeve axis. Printed standing on the
socket mouth, the saddle grows outward from the sleeve at a self-supporting
slope: web first, then retaining lips, then the complete C through the middle.

Origin is the socket mouth at Z=0, part growing along +Z; the saddle opens
toward -Y.
"""

import math

from build123d import (
    Align,
    Axis,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    Location,
    GeomType,
    Mode,
    Part,
    Plane,
    Polygon,
    Rectangle,
    add,
    chamfer,
    extrude,
    fillet,
    revolve,
)

from lib.materials import MATERIAL
from lib.pipe import CEMENT_CLEARANCE, HOOK_SHAFT_D, PIPE
from lib.retention import (
    conical_saddle_for_force,
)

# --- socket: the cemented joint onto the pipe -----------------------------
socket_bore_d = PIPE.od + CEMENT_CLEARANCE
#: Rule of thumb for a solvent joint: engage at least one pipe diameter.
minimum_socket_depth = PIPE.od * 1.4
socket_wall = 2.4
socket_od = socket_bore_d + 2 * socket_wall
#: Internal stop setting insertion depth. A shoulder, not a cap: the bore
#: continues through at the pipe's ID so the tube stays open end to end and
#: water shipped down the stick drains instead of pooling in the head.
shoulder_t = 3.0
#: Through-hole past the shoulder, matching the pipe's own bore.
drain_d = PIPE.id

# --- saddle: the clip that grips the hook shaft ---------------------------
saddle_bore_d = HOOK_SHAFT_D + 0.6
#: Throat narrower than the shaft, so the lips spread to admit it and then hold
#: by hoop tension. ~0.8x bore grips firmly while still pulling off one-handed.
throat_w = saddle_bore_d * 0.80
#: Web thickness between socket sleeve and saddle: the two tubes meet through a
#: filleted waist rather than a knife-edge tangent point.
web_t = 1.6

#: Fillet blending the saddle into the socket sleeve, the part's most loaded
#: line -- the pipe levers against the saddle here.
waist_r = 3.0
#: Chamfer leading the pipe into its socket and the shaft into the throat.
lead_in = 1.0

#: Shortest sleeve that does its own job.
minimum_socket_length = minimum_socket_depth + shoulder_t
#: Force needed to pull the stick off the hook, in newtons. The design target,
#: and the number to change if the grip is wrong: below ~25 N the clip sheds
#: itself in chop, above ~70 N it is a two-handed fight on a pitching deck.
TARGET_RELEASE_N = 40.0

#: Slope of the saddle's outer surface where it tapers, from horizontal. The
#: saddle's ends would otherwise be square annular faces, and a knock along the
#: pipe axis -- dropping the stick on deck, catching the saddle end-on against a
#: piling -- lands straight onto that corner. Tapered, the C runs out to nothing
#: at both ends and there is no square section left to hit.
#:
#: Well past 45 so the underside prints comfortably. Only the outer surface
#: slopes: the bore and throat run straight through at full size, because the
#: shaft has to pass every slice and a tapering bore would pinch it.
saddle_ramp_angle = 60.0

#: Fully formed C between the two conical end sweeps. This supplies the second
#: constraint for solving both wall thickness and total length from one force
#: target.
saddle_hold_length = 10.0
_sleeve_r = socket_od / 2

#: The saddle is placed from its *outer* radius, not its bore: the solved wall is
#: thick enough that spacing the bore off the sleeve would push the saddle's OD
#: back into the sleeve and leave the web with nothing to span. `web_t` is the
#: clear gap between the two tubes' outer surfaces, which is what the waist
#: fillets need in order to land on a rib rather than on a tangency.
#:
#: Wall and offset are mutually dependent -- the offset sets the ramp geometry
#: the solver works from, and the solved wall sets the offset -- so they are
#: iterated. The coupling is weak and settles in a couple of passes.
saddle_offset = (socket_od + saddle_bore_d) / 2 + web_t
for _ in range(8):
    saddle_wall, body_length, effective_saddle_length = conical_saddle_for_force(
        MATERIAL,
        target_force=TARGET_RELEASE_N,
        hold_length=saddle_hold_length,
        bore_d=saddle_bore_d,
        throat_w=throat_w,
        saddle_offset=saddle_offset,
        sleeve_outer_r=_sleeve_r,
        ramp_angle_deg=saddle_ramp_angle,
    )
    _next_offset = _sleeve_r + web_t + saddle_bore_d / 2 + saddle_wall
    if abs(_next_offset - saddle_offset) < 1e-9:
        break
    saddle_offset = _next_offset
saddle_ramp_rise = (body_length - saddle_hold_length) / 2
saddle_length = body_length
#: The long solved sleeve accepts the pipe to a shoulder at its far end.
socket_depth = body_length - shoulder_t
socket_length = body_length
saddle_od = saddle_bore_d + 2 * saddle_wall
#: Web narrower than either tube, so the waist fillets have somewhere to land.
web_w = saddle_od * 0.55

#: Saddle bore centre, in the sketch plane.
_saddle_c = Location((0, -saddle_offset, 0))


def hook_adapter() -> Part:
    with BuildPart() as part:
        # Socket sleeve, full length of the part.
        Cylinder(socket_od / 2, body_length, align=(None, None, None))

        # Complete C and web, before the common conical envelope trims them.
        with BuildSketch(Plane.XY):
            with BuildSketch(mode=Mode.PRIVATE) as saddle_outer:
                Circle(saddle_od / 2)
            add(saddle_outer.sketch.moved(_saddle_c))
            Rectangle(web_w, saddle_offset, align=(Align.CENTER, Align.MAX))
        extrude(amount=body_length)

        # Blend the web into both tubes before any bore is cut, so the fillets
        # follow only the outer surface. The four waist edges run the saddle's
        # full length; the sleeve's own seam edge is longer and must not be
        # picked up here.
        waist = (
            part.edges()
            .filter_by(Axis.Z)
            .filter_by(lambda e: abs(e.length - saddle_length) < 1e-6)
        )
        fillet(waist, waist_r)

        # Mirrored triangular revolutions impose one radial envelope measured
        # from the sleeve axis. The web therefore cannot protrude beyond the C:
        # both are cut by the same continuous conical surface.
        cutter_outer_r = saddle_offset + saddle_od / 2 + 1.0
        cutter_outer_z = (
            cutter_outer_r - _sleeve_r
        ) * math.tan(math.radians(saddle_ramp_angle))
        for z0, direction in ((0.0, 1.0), (body_length, -1.0)):
            with BuildSketch(Plane.XZ):
                Polygon(
                    (_sleeve_r, z0),
                    (cutter_outer_r, z0),
                    (cutter_outer_r, z0 + direction * cutter_outer_z),
                    align=None,
                )
            revolve(axis=Axis.Z, mode=Mode.SUBTRACT)

        # Socket bore: open at Z=0, stopping at the shoulder the pipe seats on.
        Cylinder(
            socket_bore_d / 2,
            socket_depth,
            align=(None, None, None),
            mode=Mode.SUBTRACT,
        )

        # Drain through the shoulder, so the head is a tube rather than a cup.
        Cylinder(
            drain_d / 2,
            body_length,
            align=(None, None, None),
            mode=Mode.SUBTRACT,
        )

        # Saddle bore, running the full height at constant diameter: the shaft
        # has to pass through every slice, so this is the one thing the taper
        # cannot touch.
        with BuildSketch(Plane.XY):
            with BuildSketch(mode=Mode.PRIVATE) as bore:
                Circle(saddle_bore_d / 2)
            add(bore.sketch.moved(_saddle_c))
        extrude(amount=saddle_length, mode=Mode.SUBTRACT)

        # Throat slot, opening toward -Y and running straight through. The
        # throat keeps its width for the whole height: it is what grips, and
        # narrowing it at the ends would only make the clip harder to fit
        # without adding any hold.
        with BuildSketch(Plane.XY):
            with BuildSketch(mode=Mode.PRIVATE) as slot:
                Rectangle(throat_w, saddle_od, align=(Align.CENTER, Align.MAX))
            add(slot.sketch.moved(_saddle_c))
        extrude(amount=saddle_length, mode=Mode.SUBTRACT)

        # Lead the pipe into the socket mouth. Selected by radius rather than by
        # "smallest circle at Z=0", which is now the drain bore.
        mouth = (
            part.edges()
            .filter_by(GeomType.CIRCLE)
            .filter_by(lambda e: abs(e.center().Z) < 1e-6)
            .filter_by(lambda e: abs(e.radius - socket_bore_d / 2) < 1e-6)
        )
        chamfer(mouth, lead_in)

        # The lips need no end break of their own. Tapering has already run them
        # out to points, so there is no square corner left at either end for an
        # axial knock to land on -- which is the whole reason for the taper.

    return part.part


if __name__ == "__main__":
    p = hook_adapter()
    print(f"valid={p.is_valid} volume={p.volume:.1f}")
    print(f"bbox={p.bounding_box()}")
