"""
Professional Courtesy drawback - can't capture non-pawn pieces with pieces of the same type
"""
import chess

def check_professional_courtesy(board, move, color):
    """Check if a move follows the professional courtesy rule"""
    
    # Only check capturing moves
    if not board.is_capture(move):
        return True
        
    # Get pieces involved
    moving_piece = board.piece_at(move.from_square)
    target_piece = board.piece_at(move.to_square)
    
    # Allow the move if either piece doesn't exist
    if not moving_piece or not target_piece:
        return True
        
    # The rule only applies to non-pawns
    if target_piece.piece_type == chess.PAWN:
        return True
        
    # Check if the pieces are the same type
    if moving_piece.piece_type == target_piece.piece_type:
        return False  # Can't capture same type
        
    return True
