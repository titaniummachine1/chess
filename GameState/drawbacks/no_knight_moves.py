import chess

def illegal_moves(board, color, move):
    """
    Blocks knight moves for the given player.
    """
    piece = board.piece_at(move.from_square)
    if piece and piece.color == color and piece.piece_type == chess.KNIGHT:
        print(f"Blocking Knight move: {move}")
        return True  # Knight move is illegal
    return False

DRAWBACK_INFO = {
    "name": "No Knight Moves",
    "illegal_moves": illegal_moves,
    "loss_condition": None,
    "piece_value_override": {
        chess.KNIGHT: 0
    }
}
