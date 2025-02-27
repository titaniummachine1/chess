import chess

# Define standard piece values for comparison (based on conventional chess values)
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000  # Kings can always be captured regardless of the drawback
}

def illegal_moves(board, color, move):
    """
    Blocks captures where the capturing piece is worth less than the captured piece.
    Exception: Any piece can capture a king.
    """
    # Get the piece that's moving
    attacker = board.piece_at(move.from_square)
    
    # Get the piece being captured (if any)
    target = board.piece_at(move.to_square)
    
    # If it's not a capture, the move is allowed
    if target is None:
        return False
    
    # Anyone can capture a king (necessary for the game to end)
    if target.piece_type == chess.KING:
        return False
    
    # Check if the attacker is trying to capture a more valuable piece
    attacker_value = PIECE_VALUES.get(attacker.piece_type, 0)
    target_value = PIECE_VALUES.get(target.piece_type, 0)
    
    # The move is illegal if the attacker is less valuable than the target
    if attacker_value < target_value:
        return True  # Block the move
    
    # Otherwise, the move is legal
    return False

DRAWBACK_INFO = {
    "name": "Punching Down",
    "description": "Your pieces can only capture pieces of equal or lesser value (exception: kings can always be captured)",
    "illegal_moves": illegal_moves,
    "loss_condition": None,
    "piece_value_override": {
        # No value overrides needed, but this changes strategy significantly
    },
    "positional_override": {
        # No positional overrides
    }
}
