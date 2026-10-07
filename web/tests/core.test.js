// Run with: node --test web/tests
const test = require("node:test");
const assert = require("node:assert");
const R = require("../core.js");

test("sexy move six times is identity", () => {
  assert.ok(new R.Cube().apply("R U R' U' ".repeat(6)).isSolved());
});

test("R move matches the Python model", () => {
  assert.strictEqual(new R.Cube().apply("R").toFacelets(),
    "UUFUUFUUFRRRRRRRRRFFDFFDFFDDDBDDBDDBLLLLLLLLLUBBUBBUBB");
});

test("facelets round trip", () => {
  for (let i = 0; i < 50; i++) {
    const c = new R.Cube().apply(R.randomScramble(30));
    assert.strictEqual(R.Cube.fromFacelets(c.toFacelets()).toFacelets(), c.toFacelets());
  }
});

test("impossible cubes are rejected", () => {
  const twisted = new R.Cube(null, [1, 0, 0, 0, 0, 0, 0, 0]);
  assert.throws(() => R.Cube.fromFacelets(twisted.toFacelets()), R.CubeError);
  assert.throws(() => R.Cube.fromFacelets("U".repeat(54)), R.CubeError);
});

test("random cubes are solved in at most 24 moves", () => {
  R.buildTables();
  for (let i = 0; i < 40; i++) {
    const c = new R.Cube().apply(R.randomScramble(30));
    const moves = R.solve(c);
    assert.ok(c.apply(moves).isSolved());
    assert.ok(moves.length <= 24, `got ${moves.length}`);
  }
});

// Turning stickers in 3D must give the same result as the cube model,
// otherwise the animation would show the wrong move.
test("3D turns match the cube model", () => {
  const rotate = (v, axis, angle) => {
    const c = Math.round(Math.cos(angle)), s = Math.round(Math.sin(angle));
    const [i, j] = [[1, 2], [2, 0], [0, 1]][axis];
    const out = v.slice();
    out[i] = v[i] * c - v[j] * s;
    out[j] = v[i] * s + v[j] * c;
    return out;
  };
  const key = (g) => g.pos.join(",") + "|" + g.normal.join(",");
  const index = {};
  for (let i = 0; i < 54; i++) index[key(R.stickerGeometry(i))] = i;
  const start = new R.Cube().apply(R.randomScramble(30));
  const before = start.toFacelets();
  for (let m = 0; m < 18; m++) {
    const { axis, layer, angle } = R.moveRotation(m);
    const after = new Array(54);
    for (let i = 0; i < 54; i++) {
      let g = R.stickerGeometry(i);
      if (g.pos[axis] === layer) g = { pos: rotate(g.pos, axis, angle), normal: rotate(g.normal, axis, angle) };
      after[index[key(g)]] = before[i];
    }
    assert.strictEqual(after.join(""), start.move(m).toFacelets(), R.MOVE_NAMES[m]);
  }
});
