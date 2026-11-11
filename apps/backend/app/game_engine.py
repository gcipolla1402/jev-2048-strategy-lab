from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable, Literal, Sequence

Direction = Literal["up", "down", "left", "right"]
Board = list[list[int]]
DIRECTIONS: tuple[Direction, ...] = ("up", "down", "left", "right")


@dataclass(frozen=True)
class MoveResult:
    board: Board
    changed: bool
    score_gained: int
    merged_positions: list[tuple[int, int]]


def _collapse(line: Sequence[int]) -> tuple[list[int], int, list[int]]:
    values = [value for value in line if value]
    collapsed: list[int] = []
    gained = 0
    merged_indices: list[int] = []
    index = 0
    while index < len(values):
        if index + 1 < len(values) and values[index] == values[index + 1]:
            merged = values[index] * 2
            collapsed.append(merged)
            gained += merged
            merged_indices.append(len(collapsed) - 1)
            index += 2
        else:
            collapsed.append(values[index])
            index += 1
    collapsed.extend([0] * (4 - len(collapsed)))
    return collapsed, gained, merged_indices


def _rows_for_direction(board: Board, direction: Direction) -> Iterable[tuple[list[int], callable]]:
    if direction == "left":
        for row in range(4):
            yield board[row][:], lambda values, row=row: [(row, col, values[col]) for col in range(4)]
    elif direction == "right":
        for row in range(4):
            yield list(reversed(board[row])), lambda values, row=row: [
                (row, 3 - col, values[col]) for col in range(4)
            ]
    elif direction == "up":
        for col in range(4):
            yield [board[row][col] for row in range(4)], lambda values, col=col: [
                (row, col, values[row]) for row in range(4)
            ]
    else:
        for col in range(4):
            yield [board[row][col] for row in range(3, -1, -1)], lambda values, col=col: [
                (3 - row, col, values[row]) for row in range(4)
            ]


def move_board(board: Board, direction: Direction) -> MoveResult:
    if direction not in DIRECTIONS:
        raise ValueError(f"Unknown direction: {direction}")
    result = [[0] * 4 for _ in range(4)]
    score_gained = 0
    merged_positions: list[tuple[int, int]] = []
    for line, place in _rows_for_direction(board, direction):
        collapsed, gained, merged_indices = _collapse(line)
        placements = place(collapsed)
        for row, col, value in placements:
            result[row][col] = value
        for merged_index in merged_indices:
            row, col, _ = placements[merged_index]
            merged_positions.append((row, col))
        score_gained += gained
    return MoveResult(result, result != board, score_gained, merged_positions)


def empty_cells(board: Board) -> list[tuple[int, int]]:
    return [(row, col) for row in range(4) for col in range(4) if board[row][col] == 0]


def add_random_tile(board: Board, rng: Random | None = None) -> tuple[Board, tuple[int, int] | None]:
    random_source = rng or Random()
    cells = empty_cells(board)
    if not cells:
        return [row[:] for row in board], None
    row, col = random_source.choice(cells)
    result = [line[:] for line in board]
    result[row][col] = 4 if random_source.random() < 0.10 else 2
    return result, (row, col)


def new_board(rng: Random | None = None) -> Board:
    random_source = rng or Random()
    board = [[0] * 4 for _ in range(4)]
    board, _ = add_random_tile(board, random_source)
    board, _ = add_random_tile(board, random_source)
    return board


def legal_moves(board: Board) -> list[Direction]:
    return [direction for direction in DIRECTIONS if move_board(board, direction).changed]


def is_game_over(board: Board) -> bool:
    return not legal_moves(board)


def has_won(board: Board) -> bool:
    return any(value >= 2048 for row in board for value in row)


def highest_tile(board: Board) -> int:
    return max((value for row in board for value in row), default=0)


def apply_move(board: Board, direction: Direction, rng: Random | None = None) -> tuple[MoveResult, tuple[int, int] | None]:
    moved = move_board(board, direction)
    if not moved.changed:
        return moved, None
    spawned_board, spawned_at = add_random_tile(moved.board, rng)
    return MoveResult(spawned_board, True, moved.score_gained, moved.merged_positions), spawned_at

