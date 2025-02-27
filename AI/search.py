import numpy as np
from GameState.movegen import DrawbackBoard
import AI.evaluation as evaluation

def score_move(board, move):
    """
    Simple move-ordering heuristic.
    1. Prefer captures, especially if capturing a high-value piece with a low-value piece.
    2. Otherwise, return a default score (0).
    """
    captured_piece = board.piece_at(move.to_square)
    if captured_piece:
        attacker = board.piece_at(move.from_square)
        # MVV-LVA approach:
        # capturedValue - (1/10)*attackerValue
        # This tries to encourage big captures and cheap attackers.
        victim_value = evaluation.get_piece_value(board, captured_piece.piece_type, captured_piece.color)
        attacker_value = evaluation.get_piece_value(board, attacker.piece_type, attacker.color)
        return victim_value * 10 - attacker_value  # scaled so that big captures stand out
    # Non-captures => 0
    return 0

def negamax(board, depth, alpha, beta):
    """
    Negamax with alpha-beta pruning and basic move-ordering.
    """
    if depth == 0 or board.is_variant_end():
        return evaluation.evaluate(board)

    max_score = -evaluation.Score.CHECKMATE.value

    # Get all legal moves
    moves = list(board.generate_legal_moves())

    if not moves:
        # No moves => losing position
        return -evaluation.Score.CHECKMATE.value

    # Sort moves by a simple heuristic: capture priority
    # Higher score_move => earlier in list => improved pruning
    moves.sort(key=lambda mv: score_move(board, mv), reverse=True)

    for move in moves:
        new_board = board.copy()
        new_board.push(move)

        score = -negamax(new_board, depth - 1, -beta, -alpha)

        if score > max_score:
            max_score = score

        alpha = max(alpha, score)
        if alpha >= beta:
            # beta cutoff
            break

    return max_score

def best_move(board, depth) -> int:
    """
    Determines the best move using Negamax with alpha-beta and basic move-ordering.
    """
    max_score = -evaluation.Score.CHECKMATE.value
    chosen_move = None

    # Gather and order moves
    moves = list(board.generate_legal_moves())
    moves.sort(key=lambda mv: score_move(board, mv), reverse=True)

    if not moves:
        print("AI has no legal moves.")
        return None

    alpha = -evaluation.Score.CHECKMATE.value
    beta = evaluation.Score.CHECKMATE.value

    for move in moves:
        new_board = board.copy()
        new_board.push(move)
        score = -negamax(new_board, depth - 1, -beta, -alpha)

        if score > max_score:
            max_score = score
            chosen_move = move

        alpha = max(alpha, score)
        if alpha >= beta:
            break

    if chosen_move is None:
        print("AI has no legal moves!")  # debugging
    else:
        print(f"AI chooses {chosen_move}, eval={max_score}")

    return chosen_move
