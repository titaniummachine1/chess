import chess

def illegal_moves(board, color, move):
    piece = board.piece_at(move.from_square)
    # Knight moves are illegal for 'color'
    return piece and piece.color == color and piece.piece_type == chess.KNIGHT

DRAWBACK_INFO = {
    "name": "No Knight Moves",
    "illegal_moves": illegal_moves,
    "loss_condition": None,
}
