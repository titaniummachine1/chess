"""
Vegan drawback - can't capture knights (horses)
"""
import chess
from typing import Optional

# Define the drawback properties
DRAWBACK_INFO = {
    "description": "You can't capture knights",
    "check_move": "check_vegan",
    "supported": True
}

def check_vegan(board: chess.Board, move: chess.Move, color: chess.Color) -> bool:
    """Check if a move follows the vegan rule"""
    assert isinstance(board, chess.Board), "Board must be a chess.Board instance"
    assert isinstance(move, chess.Move), "Move must be a chess.Move instance"
    assert color in [chess.WHITE, chess.BLACK], "Color must be chess.WHITE or chess.BLACK"
    
    # Only check capturing moves
    if not board.is_capture(move):
        return True
        
    # Get the target piece
    target_piece = board.piece_at(move.to_square)
    
    # Can't capture knights (horses)
    if target_piece and target_piece.piece_type == chess.KNIGHT:
        return False
        
    return True
