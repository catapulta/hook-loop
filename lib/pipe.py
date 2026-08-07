"""Shared datums for the docking-stick assembly.

Two independent interfaces meet in the adapter, so their dimensions live here
rather than in either part module:

* the PVC pipe the adapter is solvent-cemented onto, and
* the boat-hook shaft the adapter's saddle clips around.

Pipe sizes are nominal-inch schedule 40, whose OD bears no relation to the
nominal name (1/2" sch-40 is 21.34 mm OD), so they are tabulated from the
standard rather than computed.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PipeSpec:
    """Outside/inside diameter of a rigid pipe, in mm."""

    od: float
    id: float

    @property
    def wall(self) -> float:
        return (self.od - self.id) / 2


# ASTM D1785 schedule 40 PVC.
SCH40 = {
    '1/2"': PipeSpec(od=21.34, id=15.80),
    '3/4"': PipeSpec(od=26.67, id=20.93),
    '1"': PipeSpec(od=33.40, id=26.64),
}

#: Pipe the docking stick is built from.
PIPE = SCH40['1/2"']

#: Solvent-cement joints need a film of clearance; a printed socket also wants
#: room for extrusion width error. Total added to the pipe OD for the bore.
CEMENT_CLEARANCE = 0.4

#: Boat-hook shaft diameter at the clip-on point. Telescoping hooks run
#: 25-32 mm on their butt section; measure yours and change this one number.
HOOK_SHAFT_D = 28.0
