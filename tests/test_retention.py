"""Checks on the grip model and the saddle length it dictates.

The physics here cannot be verified against a printed part from inside a test
suite, so these pin the model's structure -- the scaling laws, the curved-beam
derivation, and the bounds the part depends on -- rather than its absolute
predictions. The one number that needs real calibration is `ROOT_COMPLIANCE`.

The straight-cantilever limit is the load-bearing test: an arc compliance that
fails to collapse to `F.L^3/3EI` as the wrap shrinks means the moment arm is
wrong, which is exactly the mistake this model was built on first time round.
"""

import math

import pytest

import hook_adapter as h
from lib.materials import MATERIAL, MATERIALS
from lib.retention import (
    RETAINING_WRAP,
    arc_compliance,
    conical_ramp_effective_length,
    conical_saddle_for_force,
    evaluate,
    length_for_force,
    ramp_effective_length,
    wrap_angle,
)


SADDLE = dict(wall=h.saddle_wall, bore_d=h.saddle_bore_d, throat_w=h.throat_w)

#: Parallel-spring equivalent length solved for the production cone.
AS_BUILT_LENGTH = h.effective_saddle_length


# --- the curved-beam derivation ------------------------------------------


def test_arc_compliance_reduces_to_a_straight_cantilever():
    """The limit that catches a wrong moment arm.

    Shrink the wrap to nothing and the arc must become a straight cantilever,
    whose tip deflection is the familiar `F.L^3/(3.E.I)`. In this model's terms
    that is `J -> phi^3/3`.
    """
    for deg in (0.1, 0.5, 1.0, 2.0):
        phi = math.radians(deg)
        assert arc_compliance(phi) == pytest.approx(phi**3 / 3, rel=1e-3)


def test_arc_compliance_matches_direct_integration():
    """Closed form against the integral it came from, `J = int sin^2(phi-t)`."""
    for deg in (30, 90, 126.9, 170):
        phi = math.radians(deg)
        steps = 20001
        total = sum(
            math.sin(phi - phi * i / (steps - 1)) ** 2 for i in range(steps)
        )
        numeric = total * phi / (steps - 1)
        assert arc_compliance(phi) == pytest.approx(numeric, rel=1e-4)


def test_arc_compliance_is_positive_and_grows_with_wrap():
    """A compliance that dips negative means the derivation is broken."""
    prev = 0.0
    for deg in range(5, 181, 5):
        got = arc_compliance(math.radians(deg))
        assert got > 0
        assert got > prev
        prev = got


def test_a_narrower_throat_wraps_further():
    tight = wrap_angle(28.6, 28.6 * 0.70)
    loose = wrap_angle(28.6, 28.6 * 0.90)
    assert tight > loose
    # Rooted at the top of the bore, a lip always wraps past a quarter circle.
    assert math.degrees(loose) > 90


def test_release_force_is_linear_in_length():
    """The property that makes length the tuning knob, and the solver exact."""
    a = evaluate(MATERIAL, length=10.0, **SADDLE)
    b = evaluate(MATERIAL, length=30.0, **SADDLE)
    assert b.release_force == pytest.approx(3 * a.release_force, rel=1e-9)


def test_stress_does_not_depend_on_length():
    """Lengthening the saddle buys grip for free; it cannot fix overstress."""
    a = evaluate(MATERIAL, length=10.0, **SADDLE)
    b = evaluate(MATERIAL, length=30.0, **SADDLE)
    assert a.peak_stress == pytest.approx(b.peak_stress, rel=1e-9)


def test_stiffer_filament_grips_harder_at_equal_geometry():
    soft = evaluate(MATERIALS["asa"], length=20.0, **SADDLE)
    stiff = evaluate(MATERIALS["pa-cf"], length=20.0, **SADDLE)
    assert stiff.release_force > soft.release_force


def test_narrower_throat_grips_harder():
    loose = evaluate(MATERIAL, length=20.0, wall=h.saddle_wall,
                     bore_d=h.saddle_bore_d, throat_w=h.saddle_bore_d * 0.90)
    tight = evaluate(MATERIAL, length=20.0, wall=h.saddle_wall,
                     bore_d=h.saddle_bore_d, throat_w=h.saddle_bore_d * 0.70)
    assert tight.release_force > loose.release_force
    assert tight.peak_stress > loose.peak_stress


def test_solver_hits_its_target():
    length = length_for_force(MATERIAL, target_force=40.0, **SADDLE)
    got = evaluate(MATERIAL, length=length, **SADDLE)
    assert got.release_force == pytest.approx(40.0, rel=1e-9)


def test_a_throat_wider_than_the_bore_is_rejected():
    """No pinch means no retention, and the model must not report a force."""
    with pytest.raises(ValueError):
        evaluate(MATERIAL, length=20.0, wall=h.saddle_wall,
                 bore_d=h.saddle_bore_d, throat_w=h.saddle_bore_d)


# --- the tapered ends -----------------------------------------------------


def test_conical_ramp_credits_only_lips_past_the_equator():
    """The long base and early lip sweep add height but no holding power."""
    rise, equivalent = conical_ramp_effective_length(
        h.saddle_bore_d,
        h.throat_w,
        1.6,
        h.saddle_offset,
        h.socket_od / 2,
        60.0,
    )
    assert equivalent < rise
    assert equivalent > 0


def test_conical_solver_closes_on_force_and_returns_total_height():
    wall, height, effective = conical_saddle_for_force(
        MATERIAL,
        target_force=40.0,
        hold_length=10.0,
        bore_d=h.saddle_bore_d,
        throat_w=h.throat_w,
        saddle_offset=h.saddle_offset,
        sleeve_outer_r=h.socket_od / 2,
        ramp_angle_deg=60.0,
    )
    result = evaluate(MATERIAL, length=effective, wall=wall,
                      bore_d=h.saddle_bore_d, throat_w=h.throat_w)
    assert result.release_force == pytest.approx(40.0, rel=1e-9)
    assert height > 10.0


def test_a_ramp_costs_less_grip_than_its_full_height_suggests():
    """Short arcs are stiffer than long ones, so tapering costs less than it looks.

    `rise` is the full physical sweep from nothing to full wrap; `equivalent`
    only credits the part of that sweep past the shaft's equator, which is a
    small fraction of the rise. If it ever inverts, the compliance curve has
    been broken.
    """
    rise, equivalent = ramp_effective_length(28.6, 28.6 * 0.80, 50.0)
    assert 0 < equivalent < rise


def test_a_steeper_ramp_is_taller():
    shallow, _ = ramp_effective_length(28.6, 28.6 * 0.80, 45.0)
    steep, _ = ramp_effective_length(28.6, 28.6 * 0.80, 60.0)
    assert steep > shallow


def test_a_throat_that_cannot_pass_the_equator_is_rejected():
    """A saddle whose lips stop short of the widest point only cradles.

    It would touch the shaft and hold nothing, and the model must say so rather
    than report a force.
    """
    with pytest.raises(ValueError):
        ramp_effective_length(28.6, 28.6, 50.0)


def test_the_taper_only_credits_the_part_that_retains():
    """Below the equator the arc cannot grip, so equivalent length ignores it.

    `rise` is the full physical sweep from nothing to full wrap, sized so the
    tip clears the shaft entirely. `equivalent` only integrates stiffness over
    the retaining portion past the equator, which is why it comes out to a
    fraction of the rise.
    """
    full = wrap_angle(28.6, 28.6 * 0.80)
    rise, equivalent = ramp_effective_length(28.6, 28.6 * 0.80, 50.0)
    from_nothing = (28.6 / 2) * math.tan(math.radians(50.0)) * full
    assert rise == pytest.approx(from_nothing, rel=1e-9)
    assert equivalent < rise / 2


# --- what the part itself commits to --------------------------------------


def test_part_is_dimensioned_for_its_release_target():
    """The saddle in the model actually delivers the force it was solved for.

    Fails if the length was clamped by the sleeve, which would silently give a
    weaker clip than `TARGET_RELEASE_N` claims.
    """
    got = evaluate(MATERIAL, length=AS_BUILT_LENGTH, **SADDLE)
    assert got.release_force == pytest.approx(h.TARGET_RELEASE_N, rel=1e-6)


def test_saddle_length_stays_within_the_sleeve():
    assert 0 < h.saddle_length <= h.body_length


def test_wall_solves_rather_than_being_chosen():
    """The taper fixes the height, so the wall is what closes on the target."""
    assert 0.4 < h.saddle_wall < 6.0
    # Several solid perimeters at a common nozzle width.
    assert h.saddle_wall / 0.4 >= 3.0


def test_saddle_does_not_yield_when_the_hook_is_clipped_in():
    """Seating the shaft must not crack or craze the lips."""
    got = evaluate(MATERIAL, length=AS_BUILT_LENGTH, **SADDLE)
    assert got.safety_factor >= 2.0, (
        f"only {got.safety_factor:.1f}x margin at "
        f"{got.peak_stress:.1f} MPa; thin the wall or widen the throat"
    )


def test_grip_survives_a_season_of_use():
    """Day-one force is not the number that matters; the settled one is.

    The stick is stored off the hook, so the lips recover between uses and only
    a small permanent set accumulates. Below roughly 25 N the clip can shake
    itself off in chop, and that floor applies to the settled force.
    """
    got = evaluate(MATERIAL, length=AS_BUILT_LENGTH, **SADDLE)
    assert got.settled_force >= 25.0, (
        f"settles to {got.settled_force:.0f} N; raise TARGET_RELEASE_N "
        "or choose a filament that takes less permanent set"
    )


def test_release_target_stays_one_handed():
    assert 25.0 <= h.TARGET_RELEASE_N <= 70.0
