"""The cube model.

A cube is stored as "cubies": where each of the 8 corners and 12 edges sits,
and how it is twisted. That makes moves simple list shuffles.

Faces are named U (up), R (right), F (front), D (down), L (left), B (back).
A cube can also be written as a 54-letter "facelet" string: the 9 stickers
of U, then R, F, D, L, B, each face read left to right, top to bottom.
"""

import random

FACES = "URFDLB"

# Corner and edge names, in the order used everywhere below.
CORNERS = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"]
EDGES = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"]

# Which sticker positions (0-53) belong to each corner / edge position.
CORNER_FACELETS = [
    (8, 9, 20), (6, 18, 38), (0, 36, 47), (2, 45, 11),
    (29, 26, 15), (27, 44, 24), (33, 53, 42), (35, 17, 51),
]
EDGE_FACELETS = [
    (5, 10), (7, 19), (3, 37), (1, 46), (32, 16), (28, 25),
    (30, 43), (34, 52), (23, 12), (21, 41), (50, 39), (48, 14),
]

SOLVED_FACELETS = "".join(f * 9 for f in FACES)


class CubeError(ValueError):
    """Raised when a cube description is impossible or malformed."""


class Cube:
    """A cube as corner/edge permutation (cp, ep) and orientation (co, eo)."""

    __slots__ = ("cp", "co", "ep", "eo")

    def __init__(self, cp=None, co=None, ep=None, eo=None):
        self.cp = list(cp) if cp is not None else list(range(8))
        self.co = list(co) if co is not None else [0] * 8
        self.ep = list(ep) if ep is not None else list(range(12))
        self.eo = list(eo) if eo is not None else [0] * 12

    def copy(self):
        return Cube(self.cp, self.co, self.ep, self.eo)

    def __eq__(self, other):
        return (self.cp, self.co, self.ep, self.eo) == (other.cp, other.co, other.ep, other.eo)

    def is_solved(self):
        return self == Cube()

    def multiply(self, other):
        """Return the cube you get by doing `self`, then `other`."""
        a, b = self, other
        return Cube(
            [a.cp[b.cp[i]] for i in range(8)],
            [(a.co[b.cp[i]] + b.co[i]) % 3 for i in range(8)],
            [a.ep[b.ep[i]] for i in range(12)],
            [(a.eo[b.ep[i]] + b.eo[i]) % 2 for i in range(12)],
        )

    def move(self, m):
        """Apply one move index (0-17, see MOVE_NAMES) and return the new cube."""
        return self.multiply(MOVE_CUBES[m])

    def apply(self, moves):
        """Apply a move string like "R U R' U'" (or a list of move indices)."""
        if isinstance(moves, str):
            moves = parse_moves(moves)
        cube = self
        for m in moves:
            cube = cube.move(m)
        return cube

    # ---- facelet strings -------------------------------------------------

    def to_facelets(self):
        f = [""] * 54
        for i in range(8):
            j, ori = self.cp[i], self.co[i]
            for n in range(3):
                f[CORNER_FACELETS[i][(n + ori) % 3]] = CORNERS[j][n]
        for i in range(12):
            j, ori = self.ep[i], self.eo[i]
            for n in range(2):
                f[EDGE_FACELETS[i][(n + ori) % 2]] = EDGES[j][n]
        for k, face in enumerate(FACES):
            f[9 * k + 4] = face
        return "".join(f)

    @classmethod
    def from_facelets(cls, text):
        """Build a cube from 54 stickers.

        Any 6 letters work: each face's colour is taken from its centre sticker,
        so "wwwwwwwww rrr..." style colour strings are fine too. Spaces are ignored.
        """
        s = "".join(text.split())
        if len(s) != 54:
            raise CubeError(f"expected 54 stickers, got {len(s)}")
        centers = [s[9 * k + 4] for k in range(6)]
        if len(set(centers)) != 6:
            raise CubeError("the six centre stickers must all be different colours")
        to_face = {c: FACES[k] for k, c in enumerate(centers)}
        try:
            s = "".join(to_face[c] for c in s)
        except KeyError as e:
            raise CubeError(f"sticker {e.args[0]!r} doesn't match any centre colour") from None
        for face in FACES:
            if s.count(face) != 9:
                raise CubeError(f"colour of face {face} appears {s.count(face)} times, not 9")

        cube = cls()
        for i in range(8):
            stickers = [s[p] for p in CORNER_FACELETS[i]]
            ori = next((o for o in range(3) if stickers[o] in "UD"), None)
            if ori is None:
                raise CubeError(f"corner at {CORNERS[i]} has no U/D sticker")
            name = stickers[ori] + stickers[(ori + 1) % 3] + stickers[(ori + 2) % 3]
            if name not in CORNERS:
                raise CubeError(f"corner at {CORNERS[i]} has impossible colours {name}")
            cube.cp[i], cube.co[i] = CORNERS.index(name), ori
        for i in range(12):
            a, b = (s[p] for p in EDGE_FACELETS[i])
            if a + b in EDGES:
                cube.ep[i], cube.eo[i] = EDGES.index(a + b), 0
            elif b + a in EDGES:
                cube.ep[i], cube.eo[i] = EDGES.index(b + a), 1
            else:
                raise CubeError(f"edge at {EDGES[i]} has impossible colours {a}{b}")
        cube.check()
        return cube

    def check(self):
        """Raise CubeError unless this cube can be reached by turning faces."""
        if sorted(self.cp) != list(range(8)):
            raise CubeError("some corner appears twice (check the sticker colours)")
        if sorted(self.ep) != list(range(12)):
            raise CubeError("some edge appears twice (check the sticker colours)")
        if sum(self.co) % 3:
            raise CubeError("a corner is twisted; this cube can't be solved without taking it apart")
        if sum(self.eo) % 2:
            raise CubeError("an edge is flipped; this cube can't be solved without taking it apart")
        if _parity(self.cp) != _parity(self.ep):
            raise CubeError("two pieces are swapped; this cube can't be solved without taking it apart")


def _parity(perm):
    p = 0
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            if perm[i] > perm[j]:
                p ^= 1
    return p


# ---- moves ------------------------------------------------------------------

# One clockwise quarter turn of each face, as "which piece lands here".
_BASIC = {
    "U": Cube([3, 0, 1, 2, 4, 5, 6, 7], [0] * 8,
              [3, 0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11], [0] * 12),
    "R": Cube([4, 1, 2, 0, 7, 5, 6, 3], [2, 0, 0, 1, 1, 0, 0, 2],
              [8, 1, 2, 3, 11, 5, 6, 7, 4, 9, 10, 0], [0] * 12),
    "F": Cube([1, 5, 2, 3, 0, 4, 6, 7], [1, 2, 0, 0, 2, 1, 0, 0],
              [0, 9, 2, 3, 4, 8, 6, 7, 1, 5, 10, 11], [0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0]),
    "D": Cube([0, 1, 2, 3, 5, 6, 7, 4], [0] * 8,
              [0, 1, 2, 3, 5, 6, 7, 4, 8, 9, 10, 11], [0] * 12),
    "L": Cube([0, 2, 6, 3, 4, 1, 5, 7], [0, 1, 2, 0, 0, 2, 1, 0],
              [0, 1, 10, 3, 4, 5, 9, 7, 8, 2, 6, 11], [0] * 12),
    "B": Cube([0, 1, 3, 7, 4, 5, 2, 6], [0, 0, 1, 2, 0, 0, 2, 1],
              [0, 1, 2, 11, 4, 5, 6, 10, 8, 9, 3, 7], [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1]),
}

# Move index m = 3 * face + (turns - 1):  0=U, 1=U2, 2=U', 3=R, ...
MOVE_NAMES = [f + s for f in FACES for s in ("", "2", "'")]
MOVE_CUBES = []
for _f in FACES:
    _c = Cube()
    for _ in range(3):
        _c = _c.multiply(_BASIC[_f])
        MOVE_CUBES.append(_c)


def parse_moves(text):
    """Turn "R U2 F'" into move indices. Also accepts Ri / R3 for R'."""
    moves = []
    for tok in text.replace(",", " ").split():
        face, suffix = tok[0].upper(), tok[1:]
        if face not in FACES:
            raise CubeError(f"unknown move {tok!r}")
        turns = {"": 1, "1": 1, "2": 2, "2'": 2, "'": 3, "i": 3, "3": 3, "’": 3}.get(suffix)
        if turns is None:
            raise CubeError(f"unknown move {tok!r}")
        moves.append(3 * FACES.index(face) + turns - 1)
    return moves


def format_moves(moves):
    return " ".join(MOVE_NAMES[m] for m in moves)


def random_scramble(length=25, rng=None):
    """A random move sequence that never turns the same face twice in a row."""
    rng = rng or random.Random()
    moves, last = [], -1
    while len(moves) < length:
        m = rng.randrange(18)
        if m // 3 == last:
            continue
        moves.append(m)
        last = m // 3
    return moves
