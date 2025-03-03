"""
Vegan drawback - can't capture knights
"""
import chess

def check_vegan(board, move, color):
    """Check if a move follows the vegan rule"""
    
    # Only check capturing moves
    if not board.is_capture(move):
        return True
        
    # Get target piece
    target_piece = board.piece_at(move.to_square)
    
    # Check if target is a knight
    if target_piece and target_piece.piece_type == chess.KNIGHT:
        return False  # Can't capture knights
        
    return True
