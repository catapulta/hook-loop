"""The sourced PVC pipe shaft of the docking stick.

Not a printed part: a plain length of schedule-40 pipe, modelled only so the
adapter's socket can be checked against it in assembly. Axis is +Z with the
cemented end at Z=0, matching the adapter's socket mouth.
"""

from build123d import BuildPart, Cylinder, Mode, Part

from lib.pipe import PIPE

#: Long enough to reach the water from a foredeck; cut to taste.
PIPE_LENGTH = 900.0


def pvc_pipe(length: float = PIPE_LENGTH) -> Part:
    with BuildPart() as pipe:
        Cylinder(PIPE.od / 2, length, align=(None, None, None))
        Cylinder(PIPE.id / 2, length, align=(None, None, None), mode=Mode.SUBTRACT)
    return pipe.part


if __name__ == "__main__":
    print(pvc_pipe())
