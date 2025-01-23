import chess

def no_bishop_moves(board, move):
    """Prevents bishops from moving."""
    return board.piece_at(move.from_square).piece_type != chess.BISHOP

DRAWBACK_INFO = {
    "legal_moves": no_bishop_moves,
    "loss_condition": None  # No special loss condition
}
