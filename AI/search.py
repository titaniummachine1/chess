import numpy as np
from GameState.movegen import DrawbackBoard
import AI.evaluation as evaluation

def negamax(board, depth):
    if depth == 0 or board.is_variant_end():
        return evaluation.evaluate(board)

    max_score = -evaluation.Score.CHECKMATE.value
    legal_moves = list(board.generate_legal_moves())

    # If no legal moves, return losing score
    if not legal_moves:
        return -evaluation.Score.CHECKMATE.value

    for move in legal_moves:
        new_board = board.copy()
        new_board.push(move)
        score = -negamax(new_board, depth - 1)
        if score > max_score:
            max_score = score
    return max_score

def best_move(board, depth):
    max_eval = -evaluation.Score.CHECKMATE.value
    chosen = None
    legal_moves = list(board.generate_legal_moves())

    if not legal_moves:
        print("AI has no moves.")
        return None

    for move in legal_moves:
        new_board = board.copy()
        new_board.push(move)
        score = -negamax(new_board, depth - 1)
        if score > max_eval:
            max_eval = score
            chosen = move

    return chosen
