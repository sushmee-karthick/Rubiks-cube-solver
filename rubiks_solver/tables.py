"""Coordinates, move tables and pruning tables for the two-phase solver.

A "coordinate" squeezes one aspect of the cube into a single number, e.g.
`twist` (0-2186) says how all corners are twisted. Move tables say how each
move changes a coordinate, and pruning tables give the fewest moves needed
to solve a pair of coordinates. Together they let the search run on plain
integers instead of whole cubes.
"""

import os
import pickle
from array import array
from math import comb, factorial
from pathlib import Path

from .cube import Cube

CACHE_VERSION = 1

N_TWIST, N_FLIP, N_SLICE = 2187, 2048, 495
N_CORNER_PERM, N_EDGE_PERM, N_SLICE_PERM = 40320, 40320, 24
SOLVED_SLICE = comb(8, 1) + comb(9, 2) + comb(10, 3) + comb(11, 4)  # slice edges at home

# U, U2, U', R2, F2, D, D2, D', L2, B2
PHASE2_MOVES = [0, 1, 2, 4, 7, 9, 10, 11, 13, 16]


# ---- coordinates --------------------------------------------------------------

def twist(c):
    t = 0
    for i in range(7):
        t = 3 * t + c.co[i]
    return t


def set_twist(c, t):
    total = 0
    for i in range(6, -1, -1):
        c.co[i] = t % 3
        total += c.co[i]
        t //= 3
    c.co[7] = -total % 3


def flip(c):
    f = 0
    for i in range(11):
        f = 2 * f + c.eo[i]
    return f


def set_flip(c, f):
    total = 0
    for i in range(10, -1, -1):
        c.eo[i] = f % 2
        total += c.eo[i]
        f //= 2
    c.eo[11] = total % 2


def slice_comb(c):
    """Which 4 of the 12 edge positions hold the middle-layer edges (FR FL BL BR)."""
    positions = [p for p in range(12) if c.ep[p] >= 8]
    return sum(comb(p, k + 1) for k, p in enumerate(positions))


def set_slice_comb(c, idx):
    positions = []
    for k in range(3, -1, -1):
        p = k
        while comb(p + 1, k + 1) <= idx:
            p += 1
        idx -= comb(p, k + 1)
        positions.append(p)
    others = iter(range(8))
    slice_edges = iter(range(8, 12))
    pos = set(positions)
    c.ep = [next(slice_edges) if p in pos else next(others) for p in range(12)]


def perm_rank(perm):
    n, r = len(perm), 0
    for i in range(n):
        smaller = sum(1 for j in range(i + 1, n) if perm[j] < perm[i])
        r += smaller * factorial(n - 1 - i)
    return r


def perm_unrank(r, n):
    items, out = list(range(n)), []
    for i in range(n - 1, -1, -1):
        q, r = divmod(r, factorial(i))
        out.append(items.pop(q))
    return out


def corner_perm(c):
    return perm_rank(c.cp)


def ud_edge_perm(c):
    """Order of the 8 top/bottom edges (only meaningful in phase 2)."""
    return perm_rank(c.ep[:8])


def slice_perm(c):
    """Order of the 4 middle-layer edges (only meaningful in phase 2)."""
    return perm_rank([e - 8 for e in c.ep[8:]])


# ---- table building -------------------------------------------------------------

def _move_table(n, setter, getter, moves):
    table = array("H", [0]) * (n * 18)
    for x in range(n):
        c = Cube()
        setter(c, x)
        for m in moves:
            table[x * 18 + m] = getter(c.move(m))
    return table


def _prune_table(t1, n1, t2, n2, start, moves):
    """Breadth-first search outward from the solved state over pairs of coordinates."""
    dist = bytearray([255]) * (n1 * n2)
    dist[start] = 0
    frontier, d = [start], 0
    while frontier:
        nxt = []
        for idx in frontier:
            a, b = divmod(idx, n2)
            a, b = a * 18, b * 18
            for m in moves:
                j = t1[a + m] * n2 + t2[b + m]
                if dist[j] == 255:
                    dist[j] = d + 1
                    nxt.append(j)
        frontier, d = nxt, d + 1
    return dist


def _set_cp(c, x):
    c.cp = perm_unrank(x, 8)


def _set_ud(c, x):
    c.ep = perm_unrank(x, 8) + [8, 9, 10, 11]


def _set_sp(c, x):
    c.ep = list(range(8)) + [8 + e for e in perm_unrank(x, 4)]


class Tables:
    FIELDS = (
        "twist_move", "flip_move", "slice_move", "cperm_move", "eperm_move", "sperm_move",
        "prune_twist_slice", "prune_flip_slice", "prune_corner_slice", "prune_edge_slice",
    )

    @classmethod
    def build(cls, log=print):
        t = cls()
        all_moves = range(18)
        log("Building move tables...")
        t.twist_move = _move_table(N_TWIST, set_twist, twist, all_moves)
        t.flip_move = _move_table(N_FLIP, set_flip, flip, all_moves)
        t.slice_move = _move_table(N_SLICE, set_slice_comb, slice_comb, all_moves)
        t.cperm_move = _move_table(N_CORNER_PERM, _set_cp, corner_perm, PHASE2_MOVES)
        t.eperm_move = _move_table(N_EDGE_PERM, _set_ud, ud_edge_perm, PHASE2_MOVES)
        t.sperm_move = _move_table(N_SLICE_PERM, _set_sp, slice_perm, PHASE2_MOVES)
        log("Building pruning tables (1/4)...")
        t.prune_twist_slice = _prune_table(t.twist_move, N_TWIST, t.slice_move, N_SLICE, SOLVED_SLICE, all_moves)
        log("Building pruning tables (2/4)...")
        t.prune_flip_slice = _prune_table(t.flip_move, N_FLIP, t.slice_move, N_SLICE, SOLVED_SLICE, all_moves)
        log("Building pruning tables (3/4)...")
        t.prune_corner_slice = _prune_table(t.cperm_move, N_CORNER_PERM, t.sperm_move, N_SLICE_PERM, 0, PHASE2_MOVES)
        log("Building pruning tables (4/4)...")
        t.prune_edge_slice = _prune_table(t.eperm_move, N_EDGE_PERM, t.sperm_move, N_SLICE_PERM, 0, PHASE2_MOVES)
        return t

    @staticmethod
    def cache_path():
        root = os.environ.get("RUBIKS_SOLVER_CACHE") or Path.home() / ".cache" / "rubiks_solver"
        return Path(root) / f"tables-v{CACHE_VERSION}.pickle"

    @classmethod
    def load(cls, log=None):
        """Load cached tables, building (and caching) them on first use."""
        import sys
        log = log or (lambda msg: print(msg, file=sys.stderr))
        path = cls.cache_path()
        if path.exists():
            with open(path, "rb") as f:
                data = pickle.load(f)
            t = cls()
            for name in cls.FIELDS:
                setattr(t, name, data[name])
            return t
        log("First run: building lookup tables (about a minute, only once)...")
        t = cls.build(log)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            pickle.dump({name: getattr(t, name) for name in cls.FIELDS}, f)
        tmp.replace(path)
        log(f"Saved tables to {path}")
        return t
