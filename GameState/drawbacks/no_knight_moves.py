import chess

def illegal_moves(board, color, move):
    """
    Return True if this move is illegal under this drawback.
    Here, any knight move is illegal for the color that has the drawback.
    """
    piece = board.piece_at(move.from_square)
    # If it's my piece and it's a knight, block the move.
    return piece is not None and piece.color == color and piece.piece_type == chess.KNIGHT

DRAWBACK_INFO = {
    "name": "No Knight Moves",
    "illegal_moves": illegal_moves,  # EXACT KEY
    "loss_condition": None
}
