"""
Get Down Mr. President drawback - can't move king when in check
"""
import chess

def check_get_down_mr_president(board, move, color):
    """Check if a move follows the get down mr president rule"""
    
    # Only apply to king moves
    moving_piece = board.piece_at(move.from_square)
    if not moving_piece or moving_piece.piece_type != chess.KING:
        return True
        
    # Check if in check
    if board.is_check():
        return False  # Can't move king when in check
        
    return True
