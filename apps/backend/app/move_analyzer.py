from __future__ import annotations

from typing import Any

from .game_engine import Board, Direction, empty_cells, highest_tile, legal_moves, move_board

CORNERS = {(0, 0), (0, 3), (3, 0), (3, 3)}


def analyze_legal_moves(board: Board) -> dict[Direction, dict[str, Any]]:
    """Return immediate, deterministic facts for every legal move.

    Simulations use ``move_board`` and therefore never mutate ``board`` or spawn
    a random tile. The function deliberately does not score or rank alternatives.
    """
    analysis: dict[Direction, dict[str, Any]] = {}
    for direction in legal_moves(board):
        result = move_board(board, direction)
        max_tile = highest_tile(result.board)
        positions = [
            [row, col]
            for row in range(4)
            for col in range(4)
            if result.board[row][col] == max_tile
        ]
        analysis[direction] = {
            "board_after": [row[:] for row in result.board],
            "empty_cells_after": len(empty_cells(result.board)),
            "merge_count": len(result.merged_positions),
            "score_gain": result.score_gained,
            "max_tile_after": max_tile,
            "max_tile_positions": positions,
            "tile_count_after": sum(value != 0 for row in result.board for value in row),
            "empty_rows_after": sum(all(value == 0 for value in row) for row in result.board),
            "empty_columns_after": sum(
                all(result.board[row][col] == 0 for row in range(4)) for col in range(4)
            ),
            "max_tile_in_corner": any(tuple(position) in CORNERS for position in positions),
        }
    return analysis

