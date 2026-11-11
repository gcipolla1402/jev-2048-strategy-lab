from random import Random

import pytest

from app.game_engine import add_random_tile, apply_move, has_won, is_game_over, move_board, new_board


@pytest.mark.parametrize(
    ("direction", "expected"),
    [
        ("left", [[4, 4, 0, 0], [2, 4, 0, 0], [4, 0, 0, 0], [0, 0, 0, 0]]),
        ("right", [[0, 0, 4, 4], [0, 0, 2, 4], [0, 0, 0, 4], [0, 0, 0, 0]]),
        ("up", [[4, 2, 8, 0], [4, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]),
        ("down", [[0, 0, 0, 0], [0, 0, 0, 0], [4, 0, 0, 0], [4, 2, 8, 0]]),
    ],
)
def test_moves_in_every_direction(direction, expected):
    board = [[2, 2, 4, 0], [2, 0, 4, 0], [4, 0, 0, 0], [0, 0, 0, 0]]
    assert move_board(board, direction).board == expected


def test_each_tile_merges_only_once():
    result = move_board([[2, 2, 2, 2], [4, 4, 8, 8], [0, 0, 0, 0], [0, 0, 0, 0]], "left")
    assert result.board[0] == [4, 4, 0, 0]
    assert result.board[1] == [8, 16, 0, 0]
    assert result.score_gained == 32


def test_chain_does_not_merge_twice_in_one_move():
    result = move_board([[4, 4, 8, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], "left")
    assert result.board[0] == [8, 8, 0, 0]
    assert result.score_gained == 8


def test_invalid_move_changes_nothing_and_spawns_nothing():
    board = [[2, 4, 8, 16], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    result, spawned_at = apply_move(board, "left", Random(1))
    assert not result.changed
    assert result.board == board
    assert spawned_at is None


def test_valid_move_spawns_exactly_one_tile():
    board = [[0, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    result, spawned_at = apply_move(board, "left", Random(4))
    assert result.changed and spawned_at is not None
    assert sum(value != 0 for row in result.board for value in row) == 2
    assert result.board[spawned_at[0]][spawned_at[1]] in {2, 4}


def test_random_tile_uses_only_two_or_four():
    values = set()
    for seed in range(100):
        board, position = add_random_tile([[0] * 4 for _ in range(4)], Random(seed))
        assert position is not None
        values.add(board[position[0]][position[1]])
    assert values == {2, 4}


def test_game_over_and_win_detection():
    blocked = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]]
    assert is_game_over(blocked)
    assert has_won([[2048, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])


def test_new_board_has_two_tiles():
    board = new_board(Random(10))
    tiles = [value for row in board for value in row if value]
    assert len(tiles) == 2
    assert set(tiles) <= {2, 4}

