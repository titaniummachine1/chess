"""
Get Down Mr. President drawback - can't move king when in check
"""
import chess
from typing import Optional

# Define the drawback properties
DRAWBACK_INFO = {
    "description": "You can't move your king when in check",
    "check_move": "check_get_down_mr_president",
    "supported": True
}

def check_get_down_mr_president(board: chess.Board, move: chess.Move, color: chess.Color) -> bool:
    """Check if a move follows the get down mr president rule"""
    assert isinstance(board, chess.Board), "Board must be a chess.Board instance"
    assert isinstance(move, chess.Move), "Move must be a chess.Move instance"
    assert color in [chess.WHITE, chess.BLACK], "Color must be chess.WHITE or chess.BLACK"
    
    # Only apply to king moves
    moving_piece = board.piece_at(move.from_square)
    if not moving_piece or moving_piece.piece_type != chess.KING:
        return True
        
    # Check if in check
    if board.is_check():
        return False  # Can't move king when in check
        
    return True
