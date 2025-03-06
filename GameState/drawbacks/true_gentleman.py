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
    """
    Check if a move follows the true gentleman rule
    
    Args:
        board: The current board state
        move: The move to check
        color: The color making the move
        
    Returns:
        True if the move is ILLEGAL (can't capture queen)
        False if the move is legal
    """
    # Get target piece
    target_piece = board.piece_at(move.to_square)
    
    # Check if this is a capture of a queen
    if target_piece and target_piece.piece_type == chess.QUEEN:
        return True  # Move is ILLEGAL - can't capture queens
        
    # All other moves are legal
    return False
