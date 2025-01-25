import numpy as np
from GameState.movegen import DrawbackBoard
import AI.evaluation as evaluation

def negamax(board, depth):
    if depth == 0:
        return evaluation.evaluate(board)

    max_score = evaluation.Score.CHECKMATE.value

    for move in board.generate_legal_moves():  # Use proper method
        new_board = board.copy()  # Ensure board state is preserved
        new_board.push(move)  # Apply move
        score = -negamax(new_board, depth - 1)
        max_score = max(score, max_score)

    return max_score


def best_move(board, depth):
    max_score = evaluation.Score.CHECKMATE.value
    best_move = None

    for move in board.generate_legal_moves():
        new_board = board.copy()
        new_board.push(move)
        score = -negamax(new_board, depth - 1)

        if score > max_score:
            max_score = score
            best_move = move

    return best_move  # Ensure best move is properly returned