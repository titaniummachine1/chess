import numpy as np
from GameState.movegen import DrawbackBoard
import AI.evaluation as evaluation

def negamax(board, depth, alpha, beta):
    """
    Implements the Negamax search algorithm with Alpha-Beta pruning.
    - AI uses drawback-aware move generation.
    - King captures are prioritized as an instant win.
    - Evaluates positions at depth = 0.
    """
    if depth == 0 or board.is_variant_end():
        return evaluation.evaluate(board)

    max_score = -evaluation.Score.CHECKMATE.value
    best_move = None

    for move in list(board.generate_legal_moves()):
        new_board = board.copy()
        new_board.push(move)
        score = -negamax(new_board, depth - 1, -beta, -alpha)

        if score > max_score:
            max_score = score
            best_move = move

        alpha = max(alpha, score)
        if alpha >= beta:
            break  # Beta cutoff

    return max_score

def best_move(board, depth):
    """
    Determines the best move using Negamax with Alpha-Beta pruning.
    - AI respects drawback-based move restrictions.
    - AI prioritizes king captures.
    """
    max_score = -evaluation.Score.CHECKMATE.value
    best_move = None

    for move in list(board.generate_legal_moves()):
        new_board = board.copy()
        new_board.push(move)
        score = -negamax(new_board, depth - 1, -evaluation.Score.CHECKMATE.value, evaluation.Score.CHECKMATE.value)

        if score > max_score:
            max_score = score
            best_move = move

    if best_move is None:
        print("AI has no legal moves!")  # Debugging info
    else:
        print(f"AI chooses move: {best_move} with evaluation {max_score}")

    return best_move
