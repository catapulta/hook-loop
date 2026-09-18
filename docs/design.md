# Adapter design

How `hook_adapter.py` is dimensioned, and why. All values are in mm and derive
from the two measured inputs in `lib/pipe.py` (`PIPE`, `HOOK_SHAFT_D`).

## Form

The adapter is two parallel tubes joined by a web:

- a **socket** sleeve, solvent-cemented onto the PVC pipe, and
- a **saddle**, a C-section that clips onto the boat-hook shaft.

Both run along the same axis. The sleeve has constant outer section; the saddle
is a complete extrusion trimmed at both ends by cones centred on the sleeve
axis. The origin is the socket mouth at `Z=0`; the saddle opens toward `-Y`.

## Socket

| Dimension | Value | Rationale |
| --- | --- | --- |
| `socket_bore_d` | pipe OD + 0.4 | Clearance for the solvent-cement film; a press fit leaves no room for glue |
| `minimum_socket_depth` | 1.4 × pipe OD | Solvent joints want at least one diameter of engagement |
| `socket_wall` | 2.4 | Several perimeters at common nozzle widths |
| `shoulder_t` | 3.0 | Sets a repeatable insertion depth |
| `rope_bore_d` | pipe ID | Rope pass-through past the shoulder |

The saddle taper sets the body length. The socket extends to a shoulder
`shoulder_t` from the far end, giving at least `minimum_socket_depth` of pipe
engagement. A `lead_in` chamfer at the mouth guides the pipe in.

The shoulder is a stop, not a cap. The bore steps down to the pipe's own inside
diameter and continues through, so the head is a tube end to end and the rope
runs the full length of the assembled stick.

That step down is to exactly the pipe ID, and the equality is the requirement
rather than a convenience. The rope bears on whatever is narrowest in the
channel; if the adapter's bore were undersize it would be the sole contact and
would chafe the rope every stroke. Held equal, the adapter presents no edge the
pipe does not already present. The step is the only place the section changes
along the length, and it adds material over material, so it does not overhang.

## Saddle

| Dimension | Value | Rationale |
| --- | --- | --- |
| `saddle_bore_d` | shaft + 0.6 | Slides freely along the shaft once seated |
| `saddle_wall` | 1.543 | Coupled force/taper solution — see below |
| `throat_w` | 0.80 × bore | The retention feature — see below |
| `saddle_offset` | tangent + `web_t` | Keeps the two tubes from meeting at a knife edge |
| `saddle_hold_length` | 10.0 | Complete C between the conical end sweeps |
| `saddle_length` | 105.79 | Total height from the coupled force/taper solution |

### Retention

The saddle holds the hook with no moving parts and no fastener. Its throat is
deliberately narrower than the shaft, so seating it spreads the two lips apart
and the C-section stores that deflection as hoop tension. Released, the lips
close back around the shaft.

The design target is `TARGET_RELEASE_N = 40` newtons: the force to pull the
stick off the hook, leaving the mooring line behind. Below roughly 25 N the clip
sheds itself in chop; above about 70 N it is a two-handed fight on a pitching
deck.

The wall and total length are solved together from that target for the filament
in `lib/materials.py`, currently ABS. The 10 mm complete-C middle supplies the
second constraint; each conical end then gets its physical rise from the solved
wall and the sleeve-axis radial envelope. The model is in `lib/retention.py`: a
curved cantilever whose lips must spread by half the interference to let the
shaft through.

- **Release force is linear in length.** The lips are a beam of section
  `length × wall`, so stiffness and spreading force both scale with it. This
  makes length the tuning knob, and makes the solver exact rather than a search.
- **Peak stress is independent of length.** Bending moment and section modulus
  scale together and cancel. Whether the clip cracks is set by wall thickness
  and throat ratio alone — lengthening an overstressed saddle fixes nothing.

At 40 N in ABS the production cone solves to a 1.543 mm wall and 105.79 mm
physical height. Its stiffness-equivalent full-C length is 40.36 mm; the
new-part release prediction is 40.0 N, the settled prediction is 36.0 N, and
the yield safety factor is 2.74.

A thicker saddle is a **more** brittle one, which is worth stating because it
inverts the usual instinct. The lips must bend 2.9 mm either way to admit the
shaft, and bending stress at a fixed deflection rises with wall thickness. Wall
thickness buys stiffness rather than stress margin; the coupled solver checks
the resulting wall against yield after closing on the force target.

### The curved-beam model

The lips are rooted where the web meets the saddle and wrap round to where the
throat chord cuts the bore — 127° at the 0.80 throat ratio. `arc_compliance`
integrates the bending moment over that arc, giving a closed form:

```
J(phi) = (phi - sin(phi)·cos(phi)) / 2      delta = F·R³·J / (E·I)
```

It reduces to `phi³/3` as the wrap shrinks, recovering the straight cantilever
`F·L³/3EI`, and a test pins that limit — it is what catches a wrong moment arm.

Two consequences are easy to get backwards. The moment arm is `R·sin(phi - t)`
at angle `t` from the root, so once the lip wraps past a quarter circle the
worst-stressed section is **mid-arc**, not the root. And curvature crowds stress
onto the inner fibre, so the straight-beam `M/Z` is corrected upward by
`CURVATURE_STRESS_FACTOR`.

The stick is stored off the hook, so the lips spend their life relaxed and
sustained-load creep never gets started. What remains is the small permanent set
that accumulates because viscoelastic recovery after each release takes hours
rather than being instant. `set_factor` derates the day-one force for that: 36 N
after a season in ABS, comfortably clear of the 25 N shake-off floor.

This is the assumption the material choice rests on. Stored clipped to the hook
instead, ABS would relax to roughly 26 N and the margin would be gone — so if
the stick ever does get left assembled, re-run the numbers with a derate nearer
0.65 or move to ASA, which is UV-stable and takes less set at the same
stiffness.

To explore the trade-offs:

```
uv run scripts/retention.py                    # what the committed part does
uv run scripts/retention.py --sweep length
uv run scripts/retention.py --sweep material
uv run scripts/retention.py --sweep throat
uv run scripts/retention.py --target 55        # solve for a different force
```

One fitted number remains: `ROOT_COMPLIANCE = 1.3`, standing for the web and
sleeve flexing rather than holding the lip roots rigid. The arc's own compliance
is derived, so this is the only guess left, and it scales release force linearly
without touching stress. Calibrate it against a luggage scale on a real pull-off:

```
ROOT_COMPLIANCE *= predicted_N / measured_N
```

A softer root than assumed means less grip than the model claims, and the saddle
wants lengthening to compensate — which the solver does automatically once the
constant is right.

The lips carry a `lead_in` radius so a shaft arriving off-axis is guided into
the throat instead of catching, and so the printed edge cannot gouge the hook.

### Sleeve-axis taper

The complete C and
its connecting web are extruded through the full body, then trimmed at both
ends by conical cutters generated by revolving triangular profiles around the
sleeve axis. At a given height the cutter admits one radial envelope measured
from that axis. The web therefore grows outward from the sleeve before the C
lips appear, the complete section is held through the middle, and the sequence
reverses at the far end.

The saddle bore and throat remain straight cuts through the complete height.
Only the outer saddle envelope is tapered, so every shaft section retains the
specified bore and throat dimensions.

#### Cone geometry

Let `d` be the distance between the sleeve and saddle axes, `Rs` the sleeve
outer radius, `R` a radius measured from the saddle axis, `phi` the angle around
the C from its root, and `alpha` the conical surface angle from horizontal. The
distance of a point on the C from the sleeve axis is

```
rho(phi, R) = sqrt(d² + R² - 2·d·R·cos(phi))
```

The lower cutter admits that point at height

```
z(phi, R) = tan(alpha) · (rho(phi, R) - Rs)
```

The upper cutter mirrors this envelope. The physical rise of one taper is set
by the last retained point on the outer lip, where the throat slot intersects
the saddle outside radius. The complete body height is

```
Hbody = Hhold + 2·Hramp
```

`Hhold` is 10 mm and `alpha` is 60° in the production part.

#### Effective gripping length

A horizontal slice whose lip ends at or before the shaft equator is an open
cradle. It can support the shaft from below but cannot oppose withdrawal
through the throat, so it contributes zero release force. Retention begins at

```
phi = pi/2
```

The base and the early lip sweep remain part of the physical taper but are not
included in effective gripping length. For the solved geometry, the cone takes
33.27 mm of each 47.90 mm ramp to reach the equator; about 69% of each ramp has
no holding power.

Slices beyond the equator act as curved springs in parallel. A slice ending at
`phi` has compliance coefficient

```
J(phi) = (phi - sin(phi)·cos(phi)) / 2
```

relative to `J(phi_full)` for the complete lip. Along the lip meanline,

```
dz/dphi = tan(alpha) · d·R·sin(phi) / rho(phi, R)
```

so one conical end has stiffness-equivalent full-C length

```
Lramp = integral[pi/2, phi_full]
        J(phi_full)/J(phi) · dz/dphi dphi
```

The numerical implementation uses midpoint integration over 1,024 intervals.
Material beyond the meanline but short of a complete outer wall is not credited
with stiffness. This treats the partially formed end of the lip
conservatively. Total effective gripping length is

```
Leffective = Hhold + 2·Lramp
```

#### Release force and coupled solve

For wall thickness `t`, the two lips are curved cantilevers of mean radius
`Rm = (bore_d + t)/2`. Their combined axial section length is `Leffective`, so
one lip has second moment

```
I = Leffective·t³/12
```

Each lip spreads by half the bore-to-throat interference. Root flexibility is
represented by the fitted `ROOT_COMPLIANCE` multiplier:

```
delta = (bore_d - throat_w)/2
k = E·I / (ROOT_COMPLIANCE · J(phi_full) · Rm³)
Fspread = k·delta
```

The throat is a wedge with `theta = asin(throat_w/bore_d)`. Resolving the two
lip forces along the withdrawal direction and including sliding friction `mu`
gives

```
Frelease = 2·Fspread ·
           (cos(theta) + mu·sin(theta)) /
           (sin(theta) - mu·cos(theta))
```

Wall and body height are coupled: changing `t` changes spring stiffness, the
outer lip radius, conical ramp height, and effective gripping length. With
`Hhold` fixed, `conical_saddle_for_force` bisects on `t`; each candidate wall
recomputes both conical ramps and evaluates `Frelease`.

For ABS, a 26.0 mm bore, a throat at 0.80 times the bore, a 60° cone, and a
40 N new-part release target, the production part solves to:

| Quantity | Solved value |
| --- | ---: |
| Wall thickness | 1.543 mm |
| Complete-C hold | 10.00 mm |
| Physical rise of each taper | 47.90 mm |
| Total body height | 105.79 mm |
| Equivalent length of each taper | 15.18 mm |
| Total effective gripping length | 40.36 mm |
| New-part release force | 40.0 N |
| Settled release force | 36.0 N |
| Peak-stress safety factor | 2.74 |

These are model predictions rather than measured forces. `ROOT_COMPLIANCE`
is 1.3 and is the sole fitted structural term; it must be calibrated from a
printed pull test. The result also assumes the ABS properties and friction in
`lib/materials.py`, full wall bonding, quasi-static withdrawal, symmetric lip
loading, elastic response, and storage with the clip released. It does not
model layer defects, impact loading, temperature-dependent modulus, geometric
contact progression, or long-term storage clipped around the shaft.

### Waist

The web between the tubes is narrower than either, leaving room for a
`waist_r = 3.0` fillet where it meets both. This is the part's most loaded line:
the pipe levers against the saddle here, and an unfilleted junction would be a
stress riser across the full length of the saddle. The fillets are applied
before any bore is cut so they follow only the outer surface.

The complete web and C are filleted before the conical cutters are subtracted.
The waist therefore follows the same axial envelope as the lips and transfers
load into the sleeve throughout the taper.

## Print orientation

The part prints standing on the socket mouth. The sleeve reaches `Z=0`; the
saddle grows outward from its surface layer by layer. Both load paths — hoop
tension in the saddle and prying at the waist — resolve within layers rather
than across the interlayer bond.

Three features vary along the length, none needing support:

- the `lead_in` chamfer flares outward over the first millimetre, at 45°, which
  self-supports;
- the shoulder steps the bore inward, adding material over material;
- the lower 60° cone grows the web and C outward from the sleeve;
- the upper cone retracts the C and web into the sleeve.

`test_base_and_lips_share_the_conical_envelope` measures the radial limit of
both ends, `test_complete_c_is_constant_through_the_hold` covers the middle,
and `test_mouth_chamfer_leads_into_constant_socket_bore` guards the socket end.

## Verification

`tests/test_hook_adapter.py` measures the built solid rather than re-reading the
parameters, so a modelling error that leaves the parameters intact still fails.
It covers: a single watertight solid, the socket bore matching pipe OD plus
clearance, the throat pinching the shaft while the bore clears it, the shoulder
stopping the pipe while leaving the tube open at both ends, the shared conical
envelope, the complete-C hold, and the socket mouth lead-in.

`tests/test_retention.py` covers the grip model. Its absolute predictions cannot
be checked without a printed part, so it pins the scaling laws instead — force
linear in length, stress independent of it — along with the bounds the part
relies on: that the solved length is not clamped, that the lips do not yield on
first fit, and that the grip still holds once the filament has relaxed.
