// Cube model + Kociemba two-phase solver, in plain JavaScript.
// The same file runs in three places:
//   - the web page (window.Rubik), for the cube model and drawing,
//   - a Web Worker, which builds the lookup tables and solves without freezing the page,
//   - Node.js (module.exports), for tests.
// It mirrors rubiks_solver/cube.py, tables.py and solver.py.

(function (root) {
  "use strict";

  const FACES = "URFDLB";
  const CORNERS = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"];
  const EDGES = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"];
  const CORNER_FACELETS = [
    [8, 9, 20], [6, 18, 38], [0, 36, 47], [2, 45, 11],
    [29, 26, 15], [27, 44, 24], [33, 53, 42], [35, 17, 51],
  ];
  const EDGE_FACELETS = [
    [5, 10], [7, 19], [3, 37], [1, 46], [32, 16], [28, 25],
    [30, 43], [34, 52], [23, 12], [21, 41], [50, 39], [48, 14],
  ];
  const SOLVED = FACES.split("").map((f) => f.repeat(9)).join("");

  class CubeError extends Error {}

  // ---- cube model ------------------------------------------------------------

  class Cube {
    constructor(cp, co, ep, eo) {
      this.cp = cp ? cp.slice() : [0, 1, 2, 3, 4, 5, 6, 7];
      this.co = co ? co.slice() : [0, 0, 0, 0, 0, 0, 0, 0];
      this.ep = ep ? ep.slice() : [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
      this.eo = eo ? eo.slice() : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    }

    multiply(b) {
      const a = this, c = new Cube();
      for (let i = 0; i < 8; i++) {
        c.cp[i] = a.cp[b.cp[i]];
        c.co[i] = (a.co[b.cp[i]] + b.co[i]) % 3;
      }
      for (let i = 0; i < 12; i++) {
        c.ep[i] = a.ep[b.ep[i]];
        c.eo[i] = (a.eo[b.ep[i]] + b.eo[i]) % 2;
      }
      return c;
    }

    move(m) { return this.multiply(MOVE_CUBES[m]); }

    apply(moves) {
      if (typeof moves === "string") moves = parseMoves(moves);
      let c = this;
      for (const m of moves) c = c.move(m);
      return c;
    }

    isSolved() { return this.toFacelets() === SOLVED; }

    toFacelets() {
      const f = new Array(54);
      for (let i = 0; i < 8; i++)
        for (let n = 0; n < 3; n++) f[CORNER_FACELETS[i][(n + this.co[i]) % 3]] = CORNERS[this.cp[i]][n];
      for (let i = 0; i < 12; i++)
        for (let n = 0; n < 2; n++) f[EDGE_FACELETS[i][(n + this.eo[i]) % 2]] = EDGES[this.ep[i]][n];
      for (let k = 0; k < 6; k++) f[9 * k + 4] = FACES[k];
      return f.join("");
    }

    static fromFacelets(text) {
      const s0 = text.replace(/\s+/g, "");
      if (s0.length !== 54) throw new CubeError(`Expected 54 stickers, got ${s0.length}.`);
      const centers = [0, 1, 2, 3, 4, 5].map((k) => s0[9 * k + 4]);
      if (new Set(centers).size !== 6) throw new CubeError("The six centre stickers must all be different colours.");
      const map = {};
      centers.forEach((c, k) => (map[c] = FACES[k]));
      let s = "";
      for (const ch of s0) {
        if (!(ch in map)) throw new CubeError(`Sticker "${ch}" doesn't match any centre colour.`);
        s += map[ch];
      }
      for (const face of FACES) {
        const n = s.split(face).length - 1;
        if (n !== 9) throw new CubeError(`${FACE_NAMES[face]} colour appears ${n} times. Each colour needs exactly 9 stickers.`);
      }
      const cube = new Cube();
      for (let i = 0; i < 8; i++) {
        const st = CORNER_FACELETS[i].map((p) => s[p]);
        let ori = st.findIndex((x) => x === "U" || x === "D");
        if (ori < 0) throw new CubeError(`The corner at ${CORNERS[i]} has no top or bottom colour, so it can't exist on a real cube.`);
        const name = st[ori] + st[(ori + 1) % 3] + st[(ori + 2) % 3];
        const j = CORNERS.indexOf(name);
        if (j < 0) throw new CubeError(`The corner at ${CORNERS[i]} has a colour combination that doesn't exist on a real cube.`);
        cube.cp[i] = j;
        cube.co[i] = ori;
      }
      for (let i = 0; i < 12; i++) {
        const a = s[EDGE_FACELETS[i][0]], b = s[EDGE_FACELETS[i][1]];
        let j = EDGES.indexOf(a + b);
        if (j >= 0) { cube.ep[i] = j; cube.eo[i] = 0; continue; }
        j = EDGES.indexOf(b + a);
        if (j >= 0) { cube.ep[i] = j; cube.eo[i] = 1; continue; }
        throw new CubeError(`The edge at ${EDGES[i]} has a colour combination that doesn't exist on a real cube.`);
      }
      cube.check();
      return cube;
    }

    check() {
      const dup = (arr) => new Set(arr).size !== arr.length;
      if (dup(this.cp)) throw new CubeError("Two corners have the same colours. Check the stickers you entered.");
      if (dup(this.ep)) throw new CubeError("Two edges have the same colours. Check the stickers you entered.");
      if (this.co.reduce((a, b) => a + b, 0) % 3)
        throw new CubeError("One corner is twisted. A real cube can't get like this by turning, so check the corner colours.");
      if (this.eo.reduce((a, b) => a + b, 0) % 2)
        throw new CubeError("One edge is flipped. A real cube can't get like this by turning, so check the edge colours.");
      if (parity(this.cp) !== parity(this.ep))
        throw new CubeError("Two pieces are swapped. A real cube can't get like this by turning, so check the colours.");
    }
  }

  const FACE_NAMES = { U: "Top", R: "Right", F: "Front", D: "Bottom", L: "Left", B: "Back" };

  function parity(p) {
    let s = 0;
    for (let i = 0; i < p.length; i++) for (let j = i + 1; j < p.length; j++) if (p[i] > p[j]) s ^= 1;
    return s;
  }

  const BASIC = {
    U: new Cube([3, 0, 1, 2, 4, 5, 6, 7], null, [3, 0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11], null),
    R: new Cube([4, 1, 2, 0, 7, 5, 6, 3], [2, 0, 0, 1, 1, 0, 0, 2], [8, 1, 2, 3, 11, 5, 6, 7, 4, 9, 10, 0], null),
    F: new Cube([1, 5, 2, 3, 0, 4, 6, 7], [1, 2, 0, 0, 2, 1, 0, 0], [0, 9, 2, 3, 4, 8, 6, 7, 1, 5, 10, 11],
      [0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0]),
    D: new Cube([0, 1, 2, 3, 5, 6, 7, 4], null, [0, 1, 2, 3, 5, 6, 7, 4, 8, 9, 10, 11], null),
    L: new Cube([0, 2, 6, 3, 4, 1, 5, 7], [0, 1, 2, 0, 0, 2, 1, 0], [0, 1, 10, 3, 4, 5, 9, 7, 8, 2, 6, 11], null),
    B: new Cube([0, 1, 3, 7, 4, 5, 2, 6], [0, 0, 1, 2, 0, 0, 2, 1], [0, 1, 2, 11, 4, 5, 6, 10, 8, 9, 3, 7],
      [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1]),
  };

  // Move index m = 3 * face + (turns - 1): 0=U, 1=U2, 2=U', 3=R, ...
  const MOVE_NAMES = [];
  const MOVE_CUBES = [];
  for (const f of FACES) {
    let c = new Cube();
    for (const s of ["", "2", "'"]) {
      c = c.multiply(BASIC[f]);
      MOVE_NAMES.push(f + s);
      MOVE_CUBES.push(c);
    }
  }

  function parseMoves(text) {
    const out = [];
    for (const tok of text.replace(/,/g, " ").split(/\s+/).filter(Boolean)) {
      const face = tok[0].toUpperCase(), suf = tok.slice(1);
      const turns = { "": 1, "1": 1, "2": 2, "2'": 2, "'": 3, "’": 3, "i": 3, "3": 3 }[suf];
      if (!FACES.includes(face) || !turns) throw new CubeError(`Unknown move "${tok}".`);
      out.push(3 * FACES.indexOf(face) + turns - 1);
    }
    return out;
  }

  const formatMoves = (moves) => moves.map((m) => MOVE_NAMES[m]).join(" ");
  const inverseMove = (m) => 3 * Math.floor(m / 3) + (2 - (m % 3));

  function randomScramble(length = 25, rand = Math.random) {
    const out = [];
    let last = -1;
    while (out.length < length) {
      const m = Math.floor(rand() * 18);
      if (Math.floor(m / 3) === last) continue;
      out.push(m);
      last = Math.floor(m / 3);
    }
    return out;
  }

  // ---- coordinates -----------------------------------------------------------

  const N_TWIST = 2187, N_FLIP = 2048, N_SLICE = 495, N_PERM8 = 40320, N_PERM4 = 24;
  const PHASE2_MOVES = [0, 1, 2, 4, 7, 9, 10, 11, 13, 16];
  const IS_PHASE2 = Array.from({ length: 18 }, (_, m) => PHASE2_MOVES.includes(m));
  const FACT = [1, 1, 2, 6, 24, 120, 720, 5040, 40320];
  const C = (n, k) => {
    if (k < 0 || k > n) return 0;
    let r = 1;
    for (let i = 0; i < k; i++) r = (r * (n - i)) / (i + 1);
    return r;
  };
  const SOLVED_SLICE = C(8, 1) + C(9, 2) + C(10, 3) + C(11, 4); // 494

  function twist(c) { let t = 0; for (let i = 0; i < 7; i++) t = 3 * t + c.co[i]; return t; }
  function setTwist(c, t) {
    let s = 0;
    for (let i = 6; i >= 0; i--) { c.co[i] = t % 3; s += c.co[i]; t = Math.floor(t / 3); }
    c.co[7] = (3 - (s % 3)) % 3;
  }
  function flip(c) { let f = 0; for (let i = 0; i < 11; i++) f = 2 * f + c.eo[i]; return f; }
  function setFlip(c, f) {
    let s = 0;
    for (let i = 10; i >= 0; i--) { c.eo[i] = f % 2; s += c.eo[i]; f = Math.floor(f / 2); }
    c.eo[11] = s % 2;
  }
  function sliceComb(c) {
    let idx = 0, k = 0;
    for (let p = 0; p < 12; p++) if (c.ep[p] >= 8) idx += C(p, ++k);
    return idx;
  }
  function setSliceComb(c, idx) {
    const pos = new Set();
    for (let k = 3; k >= 0; k--) {
      let p = k;
      while (C(p + 1, k + 1) <= idx) p++;
      idx -= C(p, k + 1);
      pos.add(p);
    }
    let o = 0, s = 8;
    for (let p = 0; p < 12; p++) c.ep[p] = pos.has(p) ? s++ : o++;
  }
  function permRank(a) {
    let r = 0;
    for (let i = 0; i < a.length; i++) {
      let smaller = 0;
      for (let j = i + 1; j < a.length; j++) if (a[j] < a[i]) smaller++;
      r += smaller * FACT[a.length - 1 - i];
    }
    return r;
  }
  function permUnrank(r, n) {
    const items = [...Array(n).keys()], out = [];
    for (let i = n - 1; i >= 0; i--) {
      const q = Math.floor(r / FACT[i]);
      r %= FACT[i];
      out.push(items.splice(q, 1)[0]);
    }
    return out;
  }
  const cornerPerm = (c) => permRank(c.cp);
  const udEdgePerm = (c) => permRank(c.ep.slice(0, 8));
  const slicePerm = (c) => permRank(c.ep.slice(8).map((e) => e - 8));

  // ---- tables ----------------------------------------------------------------

  function moveTable(n, set, get, moves) {
    const t = new Uint16Array(n * 18);
    for (let x = 0; x < n; x++) {
      const c = new Cube();
      set(c, x);
      for (const m of moves) t[x * 18 + m] = get(c.move(m));
    }
    return t;
  }

  function pruneTable(t1, n1, t2, n2, start, moves) {
    const dist = new Uint8Array(n1 * n2).fill(255);
    dist[start] = 0;
    let frontier = [start], d = 0;
    while (frontier.length) {
      const next = [];
      for (const idx of frontier) {
        const a = Math.floor(idx / n2) * 18, b = (idx % n2) * 18;
        for (const m of moves) {
          const j = t1[a + m] * n2 + t2[b + m];
          if (dist[j] === 255) { dist[j] = d + 1; next.push(j); }
        }
      }
      frontier = next;
      d++;
    }
    return dist;
  }

  let TABLES = null;
  function buildTables() {
    if (TABLES) return TABLES;
    const all = [...Array(18).keys()];
    const t = {};
    t.twistMove = moveTable(N_TWIST, setTwist, twist, all);
    t.flipMove = moveTable(N_FLIP, setFlip, flip, all);
    t.sliceMove = moveTable(N_SLICE, setSliceComb, sliceComb, all);
    t.cpermMove = moveTable(N_PERM8, (c, x) => (c.cp = permUnrank(x, 8)), cornerPerm, PHASE2_MOVES);
    t.epermMove = moveTable(N_PERM8, (c, x) => (c.ep = permUnrank(x, 8).concat([8, 9, 10, 11])), udEdgePerm, PHASE2_MOVES);
    t.spermMove = moveTable(N_PERM4, (c, x) => (c.ep = [0, 1, 2, 3, 4, 5, 6, 7].concat(permUnrank(x, 4).map((e) => e + 8))), slicePerm, PHASE2_MOVES);
    t.pruneTwistSlice = pruneTable(t.twistMove, N_TWIST, t.sliceMove, N_SLICE, SOLVED_SLICE, all);
    t.pruneFlipSlice = pruneTable(t.flipMove, N_FLIP, t.sliceMove, N_SLICE, SOLVED_SLICE, all);
    t.pruneCornerSlice = pruneTable(t.cpermMove, N_PERM8, t.spermMove, N_PERM4, 0, PHASE2_MOVES);
    t.pruneEdgeSlice = pruneTable(t.epermMove, N_PERM8, t.spermMove, N_PERM4, 0, PHASE2_MOVES);
    TABLES = t;
    return t;
  }

  // ---- two-phase search ------------------------------------------------------

  // Returns a list of move indices that solves `cube` (a Cube or a 54-sticker string).
  function solve(cube, { maxLength = 24, timeout = 20000 } = {}) {
    if (typeof cube === "string") cube = Cube.fromFacelets(cube);
    cube.check();
    if (cube.isSolved()) return [];
    const t = buildTables();
    const deadline = Date.now() + timeout;
    let nodes = 0, maxTotal = 0, result = null;
    const sol = [], sol2 = [];

    const tick = () => {
      if ((++nodes & 0xfff) === 0 && Date.now() > deadline) throw new CubeError("The search took too long. Please try again.");
    };

    function phase2(cp, ep, sp, depth, lastFace) {
      if (depth === 0) return cp === 0 && ep === 0 && sp === 0;
      tick();
      for (const m of PHASE2_MOVES) {
        const face = Math.floor(m / 3);
        if (face === lastFace || face === lastFace - 3) continue;
        const ncp = t.cpermMove[cp * 18 + m], nep = t.epermMove[ep * 18 + m], nsp = t.spermMove[sp * 18 + m];
        if (Math.max(t.pruneCornerSlice[ncp * 24 + nsp], t.pruneEdgeSlice[nep * 24 + nsp]) >= depth) continue;
        sol2.push(m);
        if (phase2(ncp, nep, nsp, depth - 1, face)) return true;
        sol2.pop();
      }
      return false;
    }

    function startPhase2() {
      const c = cube.apply(sol);
      const cp = cornerPerm(c), ep = udEdgePerm(c), sp = slicePerm(c);
      const lastFace = sol.length ? Math.floor(sol[sol.length - 1] / 3) : -1;
      const lower = Math.max(t.pruneCornerSlice[cp * 24 + sp], t.pruneEdgeSlice[ep * 24 + sp]);
      for (let d2 = lower; d2 <= maxTotal - sol.length; d2++) {
        sol2.length = 0;
        if (phase2(cp, ep, sp, d2, lastFace)) { result = sol.concat(sol2); return true; }
      }
      return false;
    }

    function phase1(tw, fl, sl, depth, lastFace) {
      if (depth === 0) {
        // A phase-1 solution ending in a phase-2 move was already tried as a shorter one.
        if (sol.length && IS_PHASE2[sol[sol.length - 1]]) return false;
        return startPhase2();
      }
      tick();
      for (let m = 0; m < 18; m++) {
        const face = Math.floor(m / 3);
        if (face === lastFace || face === lastFace - 3) continue;
        const ntw = t.twistMove[tw * 18 + m], nfl = t.flipMove[fl * 18 + m], nsl = t.sliceMove[sl * 18 + m];
        if (Math.max(t.pruneTwistSlice[ntw * 495 + nsl], t.pruneFlipSlice[nfl * 495 + nsl]) >= depth) continue;
        sol.push(m);
        if (phase1(ntw, nfl, nsl, depth - 1, face)) return true;
        sol.pop();
      }
      return false;
    }

    const tw = twist(cube), fl = flip(cube), sl = sliceComb(cube);
    const lower = Math.max(t.pruneTwistSlice[tw * 495 + sl], t.pruneFlipSlice[fl * 495 + sl]);
    for (maxTotal = maxLength; maxTotal <= 30; maxTotal++) {
      for (let d1 = lower; d1 <= maxTotal; d1++) {
        sol.length = 0;
        if (phase1(tw, fl, sl, d1, -1)) return result;
      }
    }
    throw new CubeError("No solution found.");
  }

  // ---- 3D geometry -------------------------------------------------------------
  // x points right (R), y up (U), z towards you (F). Each piece sits at -1, 0 or 1.

  // Where sticker i (0-53) sits: the piece position and the direction the sticker faces.
  function stickerGeometry(i) {
    const k = Math.floor(i / 9), r = Math.floor((i % 9) / 3), c = i % 3;
    switch (FACES[k]) {
      case "U": return { pos: [c - 1, 1, r - 1], normal: [0, 1, 0] };
      case "R": return { pos: [1, 1 - r, 1 - c], normal: [1, 0, 0] };
      case "F": return { pos: [c - 1, 1 - r, 1], normal: [0, 0, 1] };
      case "D": return { pos: [c - 1, -1, 1 - r], normal: [0, -1, 0] };
      case "L": return { pos: [-1, 1 - r, c - 1], normal: [-1, 0, 0] };
      case "B": return { pos: [1 - c, 1 - r, -1], normal: [0, 0, -1] };
    }
  }

  // How to animate a move: turn the pieces with pos[axis] === layer by `angle` radians.
  // A clockwise turn (looking at that face) is -90 degrees about the face's outward axis.
  function moveRotation(m) {
    const face = FACES[Math.floor(m / 3)], turns = (m % 3) + 1;
    const [axis, layer] = { U: [1, 1], R: [0, 1], F: [2, 1], D: [1, -1], L: [0, -1], B: [2, -1] }[face];
    const quarter = turns === 3 ? -1 : turns;
    return { axis, layer, angle: -layer * quarter * Math.PI / 2 };
  }

  const api = {
    FACES, FACE_NAMES, SOLVED, MOVE_NAMES, Cube, CubeError,
    parseMoves, formatMoves, inverseMove, randomScramble, buildTables, solve,
    stickerGeometry, moveRotation,
  };

  // Inside a Web Worker: build tables on start, then answer solve requests.
  if (typeof WorkerGlobalScope !== "undefined" && root instanceof WorkerGlobalScope) {
    root.onmessage = (e) => {
      const { id, facelets } = e.data;
      try {
        const start = Date.now();
        const moves = solve(facelets);
        root.postMessage({ id, moves, ms: Date.now() - start });
      } catch (err) {
        root.postMessage({ id, error: err instanceof CubeError ? err.message : String(err) });
      }
    };
    const start = Date.now();
    buildTables();
    root.postMessage({ ready: true, ms: Date.now() - start });
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.Rubik = api;
  }
})(typeof self !== "undefined" ? self : globalThis);
