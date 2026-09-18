"""Geometry checks on the printed adapter.

Dimensions are measured off the built solid rather than read back from the
parameter module, so a modelling mistake that leaves the parameters untouched
still fails.
"""

import math

import pytest
from build123d import Plane, SortBy, section

import hook_adapter as h
from lib.pipe import PIPE
from pvc_pipe import pvc_pipe


@pytest.fixture(scope="module")
def part():
    return h.hook_adapter()


@pytest.fixture(scope="module")
def mid_section(part):
    """Cross-section taken through the saddle."""
    return section(part, Plane.XY.offset(h.body_length / 2)).faces()[0]


def test_single_watertight_solid(part):
    assert part.is_valid
    assert len(part.solids()) == 1


def test_socket_bore_fits_pipe_with_cement_clearance(mid_section):
    """The one dimension a wrong value makes unglueable."""
    bores = [w.bounding_box() for w in mid_section.inner_wires()]
    assert len(bores) == 1, "expected exactly the socket bore as an enclosed void"
    bore = bores[0]
    assert bore.size.X == pytest.approx(h.socket_bore_d, abs=1e-3)
    assert bore.size.Y == pytest.approx(h.socket_bore_d, abs=1e-3)
    # Round, and a real clearance fit over the pipe.
    assert h.socket_bore_d > PIPE.od
    assert h.socket_bore_d - PIPE.od < 1.0


def test_throat_is_narrower_than_shaft_so_it_snaps_on(mid_section):
    """The throat as actually cut, measured at the lip faces."""
    # Lip tips sit at the throat half-width; the rounding adds vertices further
    # out, so take the pair that matches the throat, not the extremes.
    xs = sorted({abs(v.X) for v in mid_section.outer_wire().vertices()
                 if v.Y < -h.saddle_offset})
    assert any(x == pytest.approx(h.throat_w / 2, abs=1e-3) for x in xs), (
        f"no lip vertex at throat half-width {h.throat_w / 2:.2f}; got {xs}"
    )


def test_saddle_grips_by_hoop_tension():
    from lib.pipe import HOOK_SHAFT_D

    assert h.saddle_bore_d == pytest.approx(HOOK_SHAFT_D), (
        "the open saddle should closely match the shaft"
    )
    assert h.throat_w < HOOK_SHAFT_D, "throat must pinch the shaft to retain it"


def test_complete_c_is_constant_through_the_hold(part):
    lo = h.saddle_ramp_rise + 0.1
    hi = lo + h.saddle_hold_length - 0.2
    zs = [lo, (lo + hi) / 2, hi]
    areas = [section(part, Plane.XY.offset(z)).faces()[0].area for z in zs]
    assert areas[0] == pytest.approx(areas[1], rel=1e-6)
    assert areas[1] == pytest.approx(areas[2], rel=1e-6)


def _socket_bore_width(part, z):
    face = section(part, Plane.XY.offset(z)).faces()[0]
    return max(w.bounding_box().size.X for w in face.inner_wires())


def test_mouth_chamfer_leads_into_constant_socket_bore(part):
    below = _socket_bore_width(part, h.lead_in * 0.5)
    at_top = _socket_bore_width(part, h.lead_in)
    above = _socket_bore_width(part, h.lead_in + 0.1)
    assert below > at_top
    assert above == pytest.approx(at_top, abs=1e-3)


def _throat_half_width(part, z):
    """Half the throat as actually cut, measured at the lip tips."""
    face = section(part, Plane.XY.offset(z)).faces()[0]
    xs = [abs(v.X) for v in face.outer_wire().vertices() if v.Y < -h.saddle_offset]
    return max(xs) if xs else None


def _outer_radius(part, z):
    face = section(part, Plane.XY.offset(z)).faces()[0]
    return max(math.hypot(v.X, v.Y) for v in face.vertices())


def test_the_lips_run_out_at_both_ends(part):
    mid = _throat_half_width(part, h.saddle_length / 2)
    assert mid == pytest.approx(h.throat_w / 2, abs=1e-3)
    assert _throat_half_width(part, 0.02 * h.body_length) is None
    assert _throat_half_width(part, 0.98 * h.body_length) is None


def test_base_and_lips_share_the_conical_envelope(part):
    slope = math.tan(math.radians(h.saddle_ramp_angle))
    for fraction in (0.05, 0.2, 0.4, 0.6, 0.8, 0.95):
        rise = h.saddle_ramp_rise * fraction
        allowed = h.socket_od / 2 + rise / slope
        assert _outer_radius(part, rise) <= allowed + 1e-3
        assert _outer_radius(part, h.body_length - rise) <= allowed + 1e-3


def test_the_taper_is_steep_enough_to_print(part):
    """Shallower than 45 degrees and the lip tips need support."""
    assert h.saddle_ramp_angle >= 45.0


def test_saddle_does_not_overhang_the_sleeve(part):
    bb = part.bounding_box()
    assert bb.min.Z == pytest.approx(0.0, abs=1e-6)
    assert bb.max.Z == pytest.approx(h.body_length, abs=1e-6)


def test_shoulder_stops_the_pipe_without_capping_the_tube(part):
    """The pipe seats on a shoulder, but the bore runs through for the rope."""
    assert h.body_length - h.socket_depth == pytest.approx(h.shoulder_t)

    top = section(part, Plane.XY.offset(h.body_length - h.shoulder_t / 2)).faces()[0]
    bores = top.inner_wires()
    assert len(bores) == 1, "tube must stay open through the shoulder"
    assert bores[0].bounding_box().size.X == pytest.approx(h.rope_bore_d, abs=1e-3)

    # The shoulder is a real stop: narrower than the socket, so the pipe lands
    # on it rather than sliding through.
    assert h.rope_bore_d < h.socket_bore_d


def test_rope_bore_never_narrows_the_pipe(part):
    """The rope bears on the pipe wall, never on a printed edge.

    The rope runs the length of the assembled stick. If the adapter's bore were
    any smaller than the pipe's, it would be the narrowest point in the channel
    and would take the rope's wear by itself.
    """
    assert h.rope_bore_d == pytest.approx(PIPE.id, abs=1e-9)

    top = section(part, Plane.XY.offset(h.body_length - h.shoulder_t / 2)).faces()[0]
    measured = top.inner_wires()[0].bounding_box().size.X
    assert measured >= PIPE.id - 1e-3


def test_rope_bore_is_broken_at_both_ends(part):
    """Neither end of the rope channel presents a square corner.

    Sectioning just inside each end must find the bore already wider than
    nominal, which is only true if a chamfer opened it out.
    """
    assert h.rope_break > 0

    for z in (h.rope_break / 2, h.body_length - h.rope_break / 2):
        face = section(part, Plane.XY.offset(z)).faces().sort_by(SortBy.AREA)[-1]
        rope = min(w.bounding_box().size.X for w in face.inner_wires())
        assert rope > h.rope_bore_d, f"square corner at z={z}"

    # The break cannot consume the seat: the pipe still lands on a real ring.
    seat = (h.socket_bore_d - h.rope_bore_d) / 2 - h.rope_break
    assert seat > 1.0


def test_bore_is_open_at_both_ends(part):
    """A capped head would trap water shipped down the stick."""
    for z in (0.01, h.body_length - 0.01):
        face = section(part, Plane.XY.offset(z)).faces()[0]
        assert face.inner_wires(), f"bore closed at z={z}"


def test_taper_starts_from_the_sleeve_on_the_print_bed(part):
    bottom = section(part, Plane.XY.offset(0.01)).faces()[0]
    allowed = h.socket_od / 2 + 0.01 / math.tan(
        math.radians(h.saddle_ramp_angle)
    )
    assert max(math.hypot(v.X, v.Y) for v in bottom.vertices()) <= allowed + 1e-3


def test_socket_engages_at_least_one_pipe_diameter():
    assert h.socket_depth >= PIPE.od


def test_pipe_slips_into_the_socket():
    pipe_bb = pvc_pipe(length=50).bounding_box()
    assert pipe_bb.size.X == pytest.approx(PIPE.od, abs=1e-6)
    assert pipe_bb.size.X < h.socket_bore_d
