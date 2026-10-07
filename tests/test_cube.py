import pytest

from rubiks_solver.cube import SOLVED_FACELETS, Cube, CubeError, format_moves, parse_moves, random_scramble


def test_solved_cube_round_trips():
    assert Cube().to_facelets() == SOLVED_FACELETS
    assert Cube.from_facelets(SOLVED_FACELETS).is_solved()


def test_every_move_four_times_is_identity():
    for face in "URFDLB":
        assert Cube().apply(f"{face} {face} {face} {face}").is_solved()


def test_sexy_move_six_times_is_identity():
    assert Cube().apply("R U R' U' " * 6).is_solved()


def test_move_then_inverse_is_identity():
    seq = random_scramble(40)
    inverse = [3 * (m // 3) + (2 - m % 3) for m in reversed(seq)]
    assert Cube().apply(seq).apply(inverse).is_solved()


def test_r_move_stickers():
    assert Cube().apply("R").to_facelets() == (
        "UUFUUFUUF" "RRRRRRRRR" "FFDFFDFFD" "DDBDDBDDB" "LLLLLLLLL" "UBBUBBUBB"
    )


def test_facelets_round_trip_on_scrambles():
    for _ in range(50):
        c = Cube().apply(random_scramble(30))
        assert Cube.from_facelets(c.to_facelets()) == c


def test_any_colour_letters_work():
    colours = SOLVED_FACELETS.translate(str.maketrans("URFDLB", "wrgyob"))
    assert Cube.from_facelets(colours).is_solved()


def test_parse_and_format():
    assert format_moves(parse_moves("R U2 F' Di b3")) == "R U2 F' D' B'"
    with pytest.raises(CubeError):
        parse_moves("X")


@pytest.mark.parametrize("bad", [
    "U" * 54,                                   # wrong colour counts
    SOLVED_FACELETS[:-1],                       # too short
])
def test_bad_input_is_rejected(bad):
    with pytest.raises(CubeError):
        Cube.from_facelets(bad)


def test_impossible_cubes_are_rejected():
    twisted = Cube(co=[1, 0, 0, 0, 0, 0, 0, 0])
    flipped = Cube(eo=[1] + [0] * 11)
    swapped = Cube(ep=[1, 0] + list(range(2, 12)))
    for c in (twisted, flipped, swapped):
        with pytest.raises(CubeError):
            Cube.from_facelets(c.to_facelets())
