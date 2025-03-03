"""
True Gentleman drawback: Can't capture queens.
"""
import chess

DRAWBACK_INFO = {
    "name": "True Gentleman",
    "description": "You can't capture queens",
    "check_move": "check_true_gentleman",
    "supported": True
}

def check_true_gentleman(board, move, color):
    """Check if a move follows the true gentleman rule"""
    
    # Only check capturing moves
    if not board.is_capture(move):
        return True
        
    # Get target piece
    target_piece = board.piece_at(move.to_square)
    
    # Check if target is a queen
    if target_piece and target_piece.piece_type == chess.QUEEN:
        return False  # Can't capture queens
        
    return True  # Legal move
