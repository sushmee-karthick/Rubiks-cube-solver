"""Kociemba's two-phase algorithm.

Phase 1 turns any cube into one that can be finished using only
U, D, R2, L2, F2, B2 (all corners and edges "oriented", middle-layer edges
in the middle layer). Phase 2 then solves it with just those moves.
Each phase is a depth-first search guided by lookup tables that say
"you need at least N more moves from here", so dead ends are skipped.

The tables take about a minute to build the first time and are then
cached on disk (see tables.py).
"""

import time

from .cube import Cube, CubeError, format_moves
from .tables import (
    N_SLICE_PERM, PHASE2_MOVES, SOLVED_SLICE, Tables,
    corner_perm, slice_comb, slice_perm, ud_edge_perm, flip, twist,
)

_IS_PHASE2_MOVE = [m in PHASE2_MOVES for m in range(18)]


class SolveTimeout(RuntimeError):
    pass


class Solver:
    def __init__(self, tables=None):
        self.t = tables or Tables.load()

    def solve(self, cube, max_length=24, timeout=20.0):
        """Return a list of move indices that solves `cube`.

        Searches for a solution of at most `max_length` moves; if none is
        found the limit is relaxed one move at a time until `timeout` seconds.
        """
        if isinstance(cube, str):
            cube = Cube.from_facelets(cube)
        cube.check()
        if cube.is_solved():
            return []
        self._cube = cube
        self._deadline = time.monotonic() + timeout
        self._nodes = 0
        for limit in range(max_length, 31):
            self._max_total = limit
            tw, fl, sl = start = (twist(cube), flip(cube), slice_comb(cube))
            lower = max(self.t.prune_twist_slice[tw * 495 + sl], self.t.prune_flip_slice[fl * 495 + sl])
            for depth1 in range(lower, limit + 1):
                self._sol = []
                if self._phase1(*start, depth1, -1):
                    return self._result
        raise CubeError("no solution found (this should not happen)")

    def solve_string(self, cube, **kw):
        return format_moves(self.solve(cube, **kw))

    # ---- phase 1 -----------------------------------------------------------

    def _phase1(self, tw, fl, sl, depth, last_face):
        t = self.t
        if depth == 0:
            # In the target group. Ending with a phase-2 move means a shorter
            # phase 1 exists that we already tried, so skip it.
            if self._sol and _IS_PHASE2_MOVE[self._sol[-1]]:
                return False
            return self._start_phase2()
        self._tick()
        for m in range(18):
            face = m // 3
            if face == last_face or face == last_face - 3:
                continue
            ntw, nfl, nsl = t.twist_move[tw * 18 + m], t.flip_move[fl * 18 + m], t.slice_move[sl * 18 + m]
            if max(t.prune_twist_slice[ntw * 495 + nsl], t.prune_flip_slice[nfl * 495 + nsl]) >= depth:
                continue
            self._sol.append(m)
            if self._phase1(ntw, nfl, nsl, depth - 1, face):
                return True
            self._sol.pop()
        return False

    # ---- phase 2 -----------------------------------------------------------

    def _start_phase2(self):
        c = self._cube.apply(self._sol)
        cp, ep, sp = corner_perm(c), ud_edge_perm(c), slice_perm(c)
        last_face = self._sol[-1] // 3 if self._sol else -1
        t = self.t
        lower = max(t.prune_corner_slice[cp * N_SLICE_PERM + sp], t.prune_edge_slice[ep * N_SLICE_PERM + sp])
        room = self._max_total - len(self._sol)
        for depth2 in range(lower, room + 1):
            self._sol2 = []
            if self._phase2(cp, ep, sp, depth2, last_face):
                self._result = self._sol + self._sol2
                return True
        return False

    def _phase2(self, cp, ep, sp, depth, last_face):
        if depth == 0:
            return cp == 0 and ep == 0 and sp == 0
        self._tick()
        t = self.t
        for m in PHASE2_MOVES:
            face = m // 3
            if face == last_face or face == last_face - 3:
                continue
            ncp, nep, nsp = t.cperm_move[cp * 18 + m], t.eperm_move[ep * 18 + m], t.sperm_move[sp * 18 + m]
            if max(t.prune_corner_slice[ncp * N_SLICE_PERM + nsp], t.prune_edge_slice[nep * N_SLICE_PERM + nsp]) >= depth:
                continue
            self._sol2.append(m)
            if self._phase2(ncp, nep, nsp, depth - 1, face):
                return True
            self._sol2.pop()
        return False

    def _tick(self):
        self._nodes += 1
        if self._nodes & 0xFFF == 0 and time.monotonic() > self._deadline:
            raise SolveTimeout("gave up: search took too long")


_default = None


def solve(cube, **kw):
    """Solve a cube (a Cube or 54-letter facelet string); returns a move string."""
    global _default
    if _default is None:
        _default = Solver()
    return _default.solve_string(cube, **kw)
