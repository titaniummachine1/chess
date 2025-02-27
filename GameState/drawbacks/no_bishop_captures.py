import chess

def illegal_moves(board, color, move):
    """
    Blocks bishop captures for the given player.
    """
    piece = board.piece_at(move.from_square)
    target = board.piece_at(move.to_square)
    
    if (piece and piece.color == color and 
        piece.piece_type == chess.BISHOP and 
        target is not None):  # Attempting to capture
        # Removed print statement to avoid spamming console
        return True  # Bishop capture is illegal
    return False

DRAWBACK_INFO = {
    "name": "No Bishop Captures",
    "description": "Bishops cannot capture pieces",
    "illegal_moves": illegal_moves,
    "loss_condition": None,
    "piece_value_override": {
        # Bishop still has value but reduced due to limitation
        chess.BISHOP: 200  # Reduced from standard 330 value
    }
}
