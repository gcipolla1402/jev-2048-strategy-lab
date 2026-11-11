from app.game_engine import legal_moves
from app.jev_service import BASIC_INSTRUCTIONS, STRATEGIC_INSTRUCTIONS, build_jev_request


BOARD = [[2, 2, 4, 0], [2, 0, 4, 0], [0, 0, 0, 0], [0, 0, 0, 0]]


def test_basic_context_has_no_simulated_consequences():
    moves = legal_moves(BOARD)
    state, criteria, instructions, analysis, size = build_jev_request(BOARD, 12, moves, "basic")
    assert state == {"board": BOARD, "score": 12, "highest_tile": 4, "legal_moves": moves}
    assert set(criteria) == set(moves)
    assert instructions == BASIC_INSTRUCTIONS
    assert analysis == {}
    assert size > 0


def test_strategic_context_contains_factual_analysis_for_every_legal_move():
    moves = legal_moves(BOARD)
    basic = build_jev_request(BOARD, 12, moves, "basic")
    strategic = build_jev_request(BOARD, 12, moves, "strategic")
    state, criteria, instructions, analysis, size = strategic
    assert set(analysis) == set(moves)
    assert state["move_analysis"] == analysis
    assert instructions == STRATEGIC_INSTRUCTIONS
    assert set(criteria) == set(moves)
    assert size > basic[4]
    assert not any("best" in facts or "rank" in facts for facts in analysis.values())

