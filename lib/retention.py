"""How hard the saddle holds the boat-hook shaft, and how long it must be.

The saddle is a C-ring whose throat is narrower than the shaft. Seating it
spreads the two lips apart; released, they close back and the stored deflection
is what retains the hook. Pulling the stick off drags the shaft back out through
the throat, wedging the lips open again against that same spring.

Two numbers come out of this, and they behave differently with saddle length:

* **Release force** scales linearly with length. The lips are a beam of
  rectangular section `length x wall`, so their second moment -- and therefore
  their stiffness and the force to spread them -- is proportional to length.
  This is the knob for tuning grip.
* **Peak stress** does not depend on length at all. Both the bending moment and
  the section modulus scale with it, so they cancel. Whether the clip cracks or
  crazes is set by wall thickness and interference alone, and no amount of
  lengthening or shortening will fix a saddle that is overstressed.

That separation is why the part solves length for a target force and leaves the
wall and throat ratio as the safety-governed dimensions.

The model is a curved cantilever. The arc's own compliance is derived rather
than fitted -- `arc_compliance` integrates the bending moment over the wrap
angle, and `wrap_angle` gets that angle from the throat ratio -- so changing the
throat moves the stiffness through the geometry instead of through a guess.

One fitted number survives, `ROOT_COMPLIANCE`, standing for the web and sleeve
flexing rather than holding the lip roots rigid. It scales force linearly and is
what a measured pull-off should calibrate.
"""

import math
from dataclasses import dataclass

from lib.materials import Material


#: Extra compliance from the web and sleeve flexing rather than holding the lip
#: roots rigid, as a multiplier on the arc's own compliance. The arc integral
#: below assumes a built-in root; the real one breathes, which softens the clip
#: and lowers the release force. This is the only fitted number left in the
#: model, and the one to adjust against a measured pull-off.
ROOT_COMPLIANCE = 1.3

#: Curved beams run their peak stress higher than the straight-beam `M/Z`,
#: because the neutral axis shifts toward the centre of curvature. At this
#: part's R/t of roughly 5 the Winkler correction is about 15%.
CURVATURE_STRESS_FACTOR = 1.15


def wrap_angle(bore_d: float, throat_w: float) -> float:
    """How far each lip wraps, from its root to its tip, in radians.

    The lips are rooted where the web meets the saddle, at the top of the bore,
    and end where the throat chord cuts the bore circle. A narrower throat wraps
    further round the shaft.
    """
    return math.pi - math.asin(min(throat_w / bore_d, 1.0))


def arc_compliance(phi: float) -> float:
    """Tip-deflection coefficient `J` for a curved cantilever, `d = F.R^3.J/EI`.

    From Castigliano over the arc. A radial force at the lip tip leaves a moment
    `F.R.sin(phi - t)` at angle `t` from the root, and integrating its square
    gives a closed form:

        J(phi) = (phi - sin(phi).cos(phi)) / 2

    It reduces to `phi^3/3` for small `phi`, recovering the straight cantilever,
    and grows to `pi/2` at a full half-wrap.
    """
    return (phi - math.sin(phi) * math.cos(phi)) / 2


@dataclass(frozen=True)
class Retention:
    """Predicted behaviour of one saddle geometry in one material."""

    #: Force to pull the shaft out of the throat when new, in newtons.
    release_force: float
    #: The same after a season of snapping the clip on and off.
    settled_force: float
    #: Peak bending stress in the lips while the shaft is passing the throat.
    peak_stress: float
    #: Yield stress over peak stress. Below 1 the clip yields on first fit.
    safety_factor: float
    #: How far each lip must spread to admit the shaft, in mm.
    lip_deflection: float

    @property
    def is_safe(self) -> bool:
        return self.safety_factor >= 1.0


def _wedge_angle(bore_d: float, throat_w: float) -> float:
    """Half-angle of the wedge the shaft drives between the lips, in radians.

    The throat is a chord of the bore circle; where that chord meets the circle
    is where the shaft first touches on its way out, and the local surface
    tangent there sets how much of the lips' spring force opposes the pull.
    """
    return math.asin(min(throat_w / bore_d, 1.0))


#: A slice whose arc stops short of the shaft's equator is an open cradle: it
#: touches the shaft but cannot hold it, because there is nothing past the
#: widest point to stop the shaft lifting straight out. Only slices wrapping
#: further than this retain, so only they are counted.
RETAINING_WRAP = math.pi / 2


def ramp_effective_length(
    bore_d: float, throat_w: float, ramp_angle_deg: float
) -> tuple[float, float]:
    """Height and stiffness-equivalent length of one tapered lip end, in mm.

    Where the saddle tapers, each Z-slice is a C of the same bore and wall but a
    shorter wrap, and the slices act as springs in parallel. Returns the ramp's
    physical rise and the length of full-wrap saddle it is worth.

    The ramp sweeps the whole way, from no saddle at all to full wrap, so the
    saddle runs out to nothing at each end and there is no square section left
    anywhere for an axial knock to land on. That is what makes it tall: most of
    the sweep is below the shaft's equator.

    Only the part above `RETAINING_WRAP` is counted towards grip. Below it the
    arc stops short of the widest point and merely cradles the shaft, so it
    carries no retention however much material it has -- but it is still real
    height, and the caller has to build it.

    A short arc is far stiffer than a long one -- `arc_compliance` falls off
    steeply -- so the retaining part of a ramp is worth well over its own
    length, which is why tapering costs much less grip than its height suggests.
    """
    full = wrap_angle(bore_d, throat_w)
    if full <= RETAINING_WRAP:
        raise ValueError(
            "throat is too wide for the lips to pass the shaft equator: "
            "this saddle cradles rather than retains"
        )

    # The tip sweeps round the bore at a constant angle to horizontal, so its
    # rise per radian of wrap is fixed.
    rise_per_radian = (bore_d / 2) * math.tan(math.radians(ramp_angle_deg))
    rise = rise_per_radian * full

    # Parallel springs: integrate each retaining slice's stiffness relative to
    # full wrap. The cradle below the equator contributes nothing.
    reference = arc_compliance(full)
    steps = 512
    span = full - RETAINING_WRAP
    total = 0.0
    for i in range(steps):
        phi = RETAINING_WRAP + span * (i + 0.5) / steps
        total += reference / arc_compliance(phi)
    equivalent = total * span / steps * rise_per_radian

    return rise, equivalent


def conical_ramp_effective_length(
    bore_d: float,
    throat_w: float,
    wall: float,
    saddle_offset: float,
    sleeve_outer_r: float,
    ramp_angle_deg: float,
) -> tuple[float, float]:
    """Physical rise and equivalent grip of one sleeve-axis conical end.

    A horizontal slice survives inside a circle centred on the sleeve axis.
    As that circle expands up the cone, it first reaches the lip root and then
    advances around the C.  Lip slices act as springs in parallel, so their
    stiffness relative to the complete lip is integrated over the retaining
    part of that radial sweep.

    The returned physical rise reaches the outer lip tip and therefore sizes
    the printed body.  Equivalent length is deliberately integrated only to
    the lip meanline.  The small region where the cone has reached the meanline
    but not the complete outer wall is real material, but crediting it as a
    full-thickness spring would overpredict retention.
    """
    full = wrap_angle(bore_d, throat_w)
    if full <= RETAINING_WRAP:
        raise ValueError(
            "throat is too wide for the lips to pass the shaft equator: "
            "this saddle cradles rather than retains"
        )
    if wall <= 0:
        raise ValueError("wall must be positive")
    if saddle_offset <= 0 or sleeve_outer_r <= 0:
        raise ValueError("sleeve and saddle radii must be positive")

    slope = math.tan(math.radians(ramp_angle_deg))
    mean_r = (bore_d + wall) / 2

    def sleeve_radius(phi: float, radius: float) -> float:
        return math.sqrt(
            saddle_offset**2
            + radius**2
            - 2 * saddle_offset * radius * math.cos(phi)
        )

    # The slot intersects the outer circle at x=throat_w/2. This is the last
    # retained point reached by the cone and therefore fixes the visible rise.
    outer_r = bore_d / 2 + wall
    outer_wrap = math.pi - math.asin(min(throat_w / (2 * outer_r), 1.0))
    rise = slope * (
        sleeve_radius(outer_wrap, outer_r) - sleeve_outer_r
    )

    # z(phi) = slope * (rho(phi) - sleeve_outer_r), hence
    # dz/dphi = slope*d*R*sin(phi)/rho(phi). Integrating stiffness ratio dz
    # gives the length of complete C with the same spring stiffness.
    reference = arc_compliance(full)
    steps = 1024
    span = full - RETAINING_WRAP
    equivalent = 0.0
    for i in range(steps):
        phi = RETAINING_WRAP + span * (i + 0.5) / steps
        rho = sleeve_radius(phi, mean_r)
        dz_dphi = (
            slope * saddle_offset * mean_r * math.sin(phi) / rho
        )
        equivalent += reference / arc_compliance(phi) * dz_dphi
    equivalent *= span / steps

    return rise, equivalent


def conical_saddle_for_force(
    material: Material,
    *,
    target_force: float,
    hold_length: float,
    bore_d: float,
    throat_w: float,
    saddle_offset: float,
    sleeve_outer_r: float,
    ramp_angle_deg: float,
    wall_bounds: tuple[float, float] = (0.4, 6.0),
) -> tuple[float, float, float]:
    """Solve wall, total height, and effective grip for a conical saddle.

    The constant-section hold length supplies the second constraint needed to
    determine both wall and total axial length. The two conical ends set their
    own physical rise from the solved wall.
    """
    if target_force <= 0:
        raise ValueError("target force must be positive")
    if hold_length < 0:
        raise ValueError("hold length cannot be negative")

    def dimensions(wall: float) -> tuple[float, float, float]:
        rise, ramp_length = conical_ramp_effective_length(
            bore_d,
            throat_w,
            wall,
            saddle_offset,
            sleeve_outer_r,
            ramp_angle_deg,
        )
        effective_length = hold_length + 2 * ramp_length
        force = evaluate(
            material,
            length=effective_length,
            wall=wall,
            bore_d=bore_d,
            throat_w=throat_w,
        ).release_force
        return force, rise, effective_length

    lo, hi = wall_bounds
    if dimensions(lo)[0] > target_force:
        raise ValueError(f"even a {lo:.1f} mm wall exceeds the force target")
    if dimensions(hi)[0] < target_force:
        raise ValueError(f"even a {hi:.1f} mm wall misses the force target")

    for _ in range(80):
        mid = (lo + hi) / 2
        if dimensions(mid)[0] < target_force:
            lo = mid
        else:
            hi = mid

    wall = (lo + hi) / 2
    _, rise, effective_length = dimensions(wall)
    return wall, 2 * rise + hold_length, effective_length


def evaluate(
    material: Material,
    *,
    length: float,
    wall: float,
    bore_d: float,
    throat_w: float,
) -> Retention:
    """Predict the grip of a saddle of the given section.

    `length` is stiffness-equivalent length of full-wrap saddle, `wall` is
    radial, and the interference is whatever the throat takes out of the bore.
    A saddle with tapered ends is not its own height: convert with
    `ramp_effective_length` first.
    """
    if throat_w >= bore_d:
        raise ValueError(
            f"throat {throat_w:.2f} does not pinch a {bore_d:.2f} bore: "
            "the shaft would fall straight out"
        )

    if length <= 0:
        raise ValueError("a saddle of no length carries no load")

    mean_r = (bore_d + wall) / 2
    # Each lip spreads by half the interference to let the shaft through.
    deflection = (bore_d - throat_w) / 2

    # Curved cantilever of rectangular section: I = L.t^3/12, and a tip
    # stiffness k = E.I / (J.R^3) set by how far the lip wraps. The root is not
    # truly built in, so the arc's compliance is inflated before inverting it.
    second_moment = length * wall**3 / 12
    phi = wrap_angle(bore_d, throat_w)
    compliance = arc_compliance(phi) * ROOT_COMPLIANCE
    stiffness = material.e_modulus * second_moment / (compliance * mean_r**3)
    spread_force = stiffness * deflection

    # Resolve the lips' spring force along the pull axis. Friction fights the
    # shaft on its way out, so it adds to the release force here.
    theta = _wedge_angle(bore_d, throat_w)
    numerator = math.cos(theta) + material.friction * math.sin(theta)
    denominator = math.sin(theta) - material.friction * math.cos(theta)
    if denominator <= 0:
        raise ValueError(
            "throat is so narrow the lips self-lock: the clip would not release"
        )
    release = 2 * spread_force * numerator / denominator

    # Peak bending stress. The moment arm is `R.sin(phi - t)` at angle `t` from
    # the root, so once the lip wraps past a quarter circle the worst section is
    # mid-arc, where the arm reaches a full `R` -- not the root, which is what a
    # straight-beam intuition would pick. Curvature then crowds the stress onto
    # the inner fibre, correcting the straight-beam `M/Z` upward.
    worst_arm = mean_r * (1.0 if phi >= math.pi / 2 else math.sin(phi))
    section_modulus = length * wall**2 / 6
    stress = (
        CURVATURE_STRESS_FACTOR * spread_force * worst_arm / section_modulus
    )

    return Retention(
        release_force=release,
        settled_force=release * material.set_factor,
        peak_stress=stress,
        safety_factor=material.yield_stress / stress,
        lip_deflection=deflection,
    )


def length_for_force(
    material: Material,
    *,
    target_force: float,
    wall: float,
    bore_d: float,
    throat_w: float,
) -> float:
    """Saddle length giving `target_force` newtons of release force, in mm.

    Release force is linear in length, so this is one evaluation and a scale --
    no search. Stress is unaffected by the result; check it separately with
    `evaluate` on the length this returns.
    """
    if target_force <= 0:
        raise ValueError("target force must be positive")

    unit = evaluate(
        material, length=1.0, wall=wall, bore_d=bore_d, throat_w=throat_w
    )
    return target_force / unit.release_force


def wall_for_force(
    material: Material,
    *,
    target_force: float,
    length: float,
    bore_d: float,
    throat_w: float,
    bounds: tuple[float, float] = (0.4, 6.0),
) -> float:
    """Wall thickness giving `target_force` from a saddle of fixed length, mm.

    The question a tapered saddle asks. Its height is set by the ramp angle and
    the wrap it has to sweep, not chosen, so length is no longer the free knob
    and the wall becomes the one that closes on the target.

    Force goes as the cube of the wall while stress goes only as the wall, so
    thinning to hit a force target *raises* the safety factor. Solved by
    bisection rather than algebra because the mean radius moves with the wall.
    """
    if target_force <= 0:
        raise ValueError("target force must be positive")

    lo, hi = bounds
    common = dict(length=length, bore_d=bore_d, throat_w=throat_w)
    if evaluate(material, wall=lo, **common).release_force > target_force:
        raise ValueError(
            f"even a {lo:.1f} mm wall grips harder than {target_force:.0f} N; "
            "shorten the saddle or widen the throat"
        )
    if evaluate(material, wall=hi, **common).release_force < target_force:
        raise ValueError(
            f"even a {hi:.1f} mm wall cannot reach {target_force:.0f} N; "
            "lengthen the saddle or narrow the throat"
        )

    for _ in range(80):
        mid = (lo + hi) / 2
        if evaluate(material, wall=mid, **common).release_force < target_force:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
