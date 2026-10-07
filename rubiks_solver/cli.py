"""Command-line interface: `rubik scramble`, `rubik show`, `rubik solve`."""

import argparse
import random
import sys
import time

from .cube import Cube, CubeError, format_moves, parse_moves, random_scramble

# Background colours for each face (standard Western colour scheme).
_ANSI = {"U": 15, "R": 196, "F": 34, "D": 226, "L": 208, "B": 21}


def draw_net(facelets, color=True):
    """Draw the cube unfolded: U on top, then L F R B in a row, then D."""
    def face(k):
        return [facelets[9 * k + 3 * r: 9 * k + 3 * r + 3] for r in range(3)]

    def cell(ch):
        if not color:
            return ch + " "
        return f"\x1b[48;5;{_ANSI[ch]}m  \x1b[0m"

    def row(chars):
        return "".join(cell(ch) for ch in chars)

    U, R, F, D, L, B = (face(k) for k in range(6))
    pad = " " * 6
    lines = [pad + row(r) for r in U]
    lines += [row(L[r]) + row(F[r]) + row(R[r]) + row(B[r]) for r in range(3)]
    lines += [pad + row(r) for r in D]
    return "\n".join(lines)


def _cube_from_args(args):
    if args.scramble:
        return Cube().apply(args.scramble)
    if args.facelets:
        return Cube.from_facelets("".join(args.facelets))
    raise CubeError("give a 54-letter cube string or --scramble \"R U ...\"")


def cmd_scramble(args):
    rng = random.Random(args.seed)
    moves = random_scramble(args.length, rng)
    cube = Cube().apply(moves)
    print(format_moves(moves))
    if not args.quiet:
        print(cube.to_facelets())
        print(draw_net(cube.to_facelets(), color=not args.no_color))


def cmd_show(args):
    cube = _cube_from_args(args)
    print(cube.to_facelets())
    print(draw_net(cube.to_facelets(), color=not args.no_color))


def cmd_solve(args):
    from .solver import Solver, SolveTimeout

    cube = _cube_from_args(args)
    if args.show:
        print(draw_net(cube.to_facelets(), color=not args.no_color))
    solver = Solver()
    start = time.monotonic()
    try:
        moves = solver.solve(cube, max_length=args.max_length, timeout=args.timeout)
    except SolveTimeout as e:
        sys.exit(f"error: {e}")
    took = time.monotonic() - start
    print(format_moves(moves) if moves else "(already solved)")
    if not args.quiet:
        print(f"{len(moves)} moves, found in {took:.2f}s", file=sys.stderr)
    if args.steps:
        for i, m in enumerate(moves, 1):
            cube = cube.move(m)
            print(f"\nStep {i}: {format_moves([m])}")
            print(draw_net(cube.to_facelets(), color=not args.no_color))


def main(argv=None):
    p = argparse.ArgumentParser(prog="rubik", description="A Rubik's Cube solver (Kociemba two-phase).")
    p.add_argument("--no-color", action="store_true", help="draw the cube with letters instead of colours")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scramble", help="make a random scramble")
    s.add_argument("--length", type=int, default=25)
    s.add_argument("--seed", type=int, help="repeatable scrambles")
    s.add_argument("-q", "--quiet", action="store_true", help="only print the moves")
    s.set_defaults(func=cmd_scramble)

    for name, func, text in (("show", cmd_show, "draw a cube"), ("solve", cmd_solve, "solve a cube")):
        s = sub.add_parser(name, help=text)
        s.add_argument("facelets", nargs="*", help="54 stickers: U, R, F, D, L, B faces in order")
        s.add_argument("-s", "--scramble", help='start from a scramble, e.g. "R U R\' U\'"')
        s.set_defaults(func=func)
    solve_p = sub.choices["solve"]
    solve_p.add_argument("--max-length", type=int, default=24, help="aim for at most this many moves")
    solve_p.add_argument("--timeout", type=float, default=20.0, help="seconds before giving up")
    solve_p.add_argument("--show", action="store_true", help="draw the cube before solving")
    solve_p.add_argument("--steps", action="store_true", help="draw the cube after every move")
    solve_p.add_argument("-q", "--quiet", action="store_true", help="only print the moves")

    args = p.parse_args(argv)
    try:
        args.func(args)
    except CubeError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
