import chess

def illegal_moves(board, color, move):
    """
    Blocks knight captures for the given player.
    """
    piece = board.piece_at(move.from_square)
    target = board.piece_at(move.to_square)
    
    if (piece and piece.color == color and 
        piece.piece_type == chess.KNIGHT and 
        target is not None):  # Attempting to capture
        print(f"Blocking Knight capture: {move}")
        return True  # Knight capture is illegal
    return False

DRAWBACK_INFO = {
    "name": "No Knight Captures",
    "description": "Knights cannot capture pieces",
    "illegal_moves": illegal_moves,
    "loss_condition": None,
    "piece_value_override": {
        # Knight still has value but reduced due to limitation
        chess.KNIGHT: 200  # Reduced from standard 320 value
    }
}
