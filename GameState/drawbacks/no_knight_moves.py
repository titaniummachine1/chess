import chess

def illegal_moves(board, color, move):
    """Removes all knight moves."""
    return board.piece_type_at(move.from_square) == chess.KNIGHT

DRAWBACK_INFO = {
    "name": "No Knight Moves",
    "illegal_moves": illegal_moves,
    "loss_condition": None  # No instant loss condition
}
