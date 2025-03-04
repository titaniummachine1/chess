import chess

# Modified piece values to reflect capture limitations:
# - Pawns worth less because they can't capture other pawns effectively
# - Knights/Bishops reduced because they can't capture higher value pieces
# - Rooks slightly reduced
# - Queen increased slightly as it's less vulnerable
PIECE_VALUES = {
    chess.PAWN: 60,      # Reduced from 100 - very limited in captures
    chess.KNIGHT: 200,   # Reduced from 300 - can't capture higher pieces
    chess.BISHOP: 200,   # Reduced from 300 - can't capture higher pieces
    chess.ROOK: 400,     # Reduced from 500 - somewhat limited
    chess.QUEEN: 1100,   # Increased from 900 - more valuable as it's safer
    chess.KING: 20000    # Unchanged - can always be captured
}

def illegal_moves(board, move, color):
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
    
    # The move is illegal if the attacker is less thhen in value to the target
    if attacker_value < target_value:
        return True  # Block the move
    
    # Otherwise, the move is legal
    return False

DRAWBACK_INFO = {
    "name": "Punching Down",
    "description": "Your pieces can only capture pieces of equal or lesser value (exception: kings can always be captured)",
    "illegal_moves": illegal_moves,
    "check_move": "illegal_moves",  # Changed to a string, not function reference
    "loss_condition": None,
    "piece_value_override": PIECE_VALUES,  # Use our modified values
    "positional_override": {
        # No positional overrides
    },
    "supported": True  # Added the required supported flag
}
