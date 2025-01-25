# GameState/drawbacks/no_knight_moves.py

import chess

def illegal_moves(board, color, move):
    """
    Disallows any knight move for the given player.
    """
    piece = board.piece_at(move.from_square)
    return piece and piece.color == color and piece.piece_type == chess.KNIGHT

DRAWBACK_INFO = {
    "name": "No Knight Moves",
    "illegal_moves": illegal_moves,
    "loss_condition": None,  # No immediate loss condition
}
