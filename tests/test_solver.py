import random

from rubiks_solver import Cube, Solver, random_scramble, solve


def test_solved_cube_needs_no_moves():
    assert solve(Cube()) == ""


def test_short_scrambles():
    for scramble in ["R", "R U", "F2 B2", "R U R' U'"]:
        cube = Cube().apply(scramble)
        assert cube.apply(solve(cube)).is_solved()


def test_random_cubes_are_solved_in_at_most_24_moves():
    solver = Solver()
    rng = random.Random(2024)
    for _ in range(25):
        cube = Cube().apply(random_scramble(30, rng))
        moves = solver.solve(cube)
        assert cube.apply(moves).is_solved()
        assert len(moves) <= 24


def test_solve_accepts_facelet_string():
    cube = Cube().apply("L2 D' F B U R2")
    assert cube.apply(solve(cube.to_facelets())).is_solved()
