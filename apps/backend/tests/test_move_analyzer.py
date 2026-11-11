from copy import deepcopy

from app.game_engine import legal_moves
from app.move_analyzer import analyze_legal_moves


def test_analysis_calculates_immediate_facts_without_mutation_or_spawn():
    board = [[2, 2, 4, 0], [2, 2, 4, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    original = deepcopy(board)
    analysis = analyze_legal_moves(board)

    left = analysis["left"]
    assert left["board_after"] == [[4, 4, 0, 0], [4, 4, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    assert left["empty_cells_after"] == 12
    assert left["merge_count"] == 2
    assert left["score_gain"] == 8
    assert left["max_tile_after"] == 4
    assert [0, 0] in left["max_tile_positions"]
    assert left["tile_count_after"] == 4
    assert left["empty_rows_after"] == 2
    assert left["empty_columns_after"] == 2
    assert left["max_tile_in_corner"] is True
    assert board == original
    assert sum(value != 0 for row in left["board_after"] for value in row) == 4


def test_analysis_contains_only_legal_moves_and_no_ranking():
    board = [[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    analysis = analyze_legal_moves(board)
    assert set(analysis) == set(legal_moves(board)) == {"down", "right"}
    assert all("rank" not in facts and "recommended" not in facts for facts in analysis.values())

