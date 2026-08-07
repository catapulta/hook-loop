"""Filament properties governing how hard the saddle grips.

Values are for printed parts, not injection-moulded datasheet coupons: solid
walls, ~100% perimeter overlap, at deck temperature. The saddle's load is hoop
tension running within layers rather than across them, so the usual interlayer
knockdown barely applies and the moduli are close to bulk.

`set_factor` is the fraction of the day-one grip still present after a season of
snapping the clip on and off. The stick is stored off the hook, so the lips
spend their life relaxed and sustained-load creep never gets started; what
remains is the small permanent set that accumulates because viscoelastic
recovery after each release takes hours rather than being instant. That is a
much gentler derate than permanent deflection would demand -- if the stick ever
does get stored clipped on, these numbers are optimistic by roughly a third.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    """Elastic properties of a printed filament, in MPa where dimensional."""

    name: str
    e_modulus: float
    yield_stress: float
    #: Retained grip after a season of intermittent use, 0-1. Assumes the clip
    #: is stored off the hook; see the module docstring.
    set_factor: float
    #: Sliding friction of the shaft against the throat lips. Governs how much
    #: of the lips' spring force resists pull-out rather than just wedging.
    friction: float
    notes: str = ""


MATERIALS = {
    "abs": Material(
        name="ABS",
        e_modulus=2100.0,
        yield_stress=40.0,
        set_factor=0.90,
        friction=0.30,
        notes="Recovers well between uses; still degrades in sunlight.",
    ),
    "asa": Material(
        name="ASA",
        e_modulus=2000.0,
        yield_stress=44.0,
        set_factor=0.92,
        friction=0.30,
        notes="ABS stiffness with UV stability -- the better choice on deck.",
    ),
    "petg": Material(
        name="PETG",
        e_modulus=1900.0,
        yield_stress=47.0,
        set_factor=0.85,
        friction=0.35,
        notes="Tougher than ABS; the slowest of the three to recover its shape.",
    ),
    "pa-cf": Material(
        name="PA-CF",
        e_modulus=5500.0,
        yield_stress=85.0,
        set_factor=0.95,
        friction=0.25,
        notes="Stiff enough that the saddle wants to be much shorter.",
    ),
}


#: Filament the committed model is dimensioned for.
MATERIAL = MATERIALS["abs"]
