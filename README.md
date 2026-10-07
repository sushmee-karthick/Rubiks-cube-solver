# Rubik's Cube Solver

A Rubik's Cube solver written in plain Python, no dependencies. Give it a scrambled
cube and it prints a solution, usually around 20 to 24 moves, in under a second.

It uses **Kociemba's two-phase algorithm**:

1. **Phase 1** turns the cube into a special "half-solved" state where every piece
   is pointing the right way and the middle-layer edges are in the middle layer.
2. **Phase 2** finishes the job using only `U`, `D`, `R2`, `L2`, `F2`, `B2`.

The answer is short but not always the shortest possible: a cube scrambled with
5 moves might get a 12-move solution, because it goes via the half-solved state.

Each phase is a depth-first search guided by lookup tables that say "you need at
least N more moves from here", so the search skips hopeless paths. The tables are
built the first time you run it (about 15-60 seconds) and cached in
`~/.cache/rubiks_solver/`.

## Install

```bash
git clone https://github.com/<your-username>/rubiks-solver.git
cd rubiks-solver
pip install -e .
```

## Use it

```bash
# Make a random scramble and draw the cube
rubik scramble

# Solve the cube you get from a scramble
rubik solve --scramble "R U R' U' F2 D L' B"

# Solve a cube you typed in (54 stickers, see below)
rubik solve DFFDURLLBDURLRLRFBUURBFBLBFBDDRDLLDUBRFRLUDFUUULDBBRFF

# Watch it get solved move by move
rubik solve --scramble "R U F" --steps
```

You can also run it without installing: `python -m rubiks_solver solve ...`

### Typing in your own cube

A cube is 54 stickers, written face by face in this order: **U**p, **R**ight,
**F**ront, **D**own, **L**eft, **B**ack. Each face is read left to right, top to
bottom, like a book, while looking straight at it (for U, hold the cube so F faces
you; for D, so F faces you too; for the side faces, keep U on top).

```
             U1 U2 U3
             U4 U5 U6
             U7 U8 U9
   L1 L2 L3  F1 F2 F3  R1 R2 R3  B1 B2 B3
   L4 L5 L6  F4 F5 F6  R4 R5 R6  B4 B5 B6
   L7 L8 L9  F7 F8 F9  R7 R8 R9  B7 B8 B9
             D1 D2 D3
             D4 D5 D6
             D7 D8 D9
```

You can use any letters for colours (for example `w r g y o b`); each face's colour
is taken from its centre sticker. The solver tells you if the cube is impossible
(e.g. a corner was twisted or two stickers were swapped).

### Move notation

`R` = turn the right face clockwise (as if you were looking at it), `R'` =
anticlockwise, `R2` = half turn. Same for `U`, `F`, `D`, `L`, `B`.

## Use it from Python

```python
from rubiks_solver import Cube, solve

cube = Cube().apply("R U R' U' F2")
print(solve(cube))   # a move string like "F2 U R U' R U2 D2 ..."
```

## Project layout

```
rubiks_solver/
  cube.py     the cube model: pieces, moves, sticker strings
  tables.py   coordinates and lookup tables for the solver
  solver.py   the two-phase search
  cli.py      the `rubik` command
tests/        pytest tests
```

## Run the tests

```bash
pip install -e ".[test]"
pytest
```

## Ideas for later

- A 3D cube in the browser that animates the solution
- Read a real cube's colours from a webcam photo
- Keep searching for shorter solutions when there's time left

## License

MIT
