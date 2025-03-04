"""
Forward March drawback - can't move backwards
"""
import chess
from typing import Optional

# Define the drawback properties
DRAWBACK_INFO = {
    "description": "Can't move backwards",
    "check_move": "check_forward_march",
    "supported": True
}

def check_forward_march(board: chess.Board, move: chess.Move, color: chess.Color) -> bool:
    """Check if a move follows the forward march rule"""
    assert isinstance(board, chess.Board), "Board must be a chess.Board instance"
    assert isinstance(move, chess.Move), "Move must be a chess.Move instance"
    assert color in [chess.WHITE, chess.BLACK], "Color must be chess.WHITE or chess.BLACK"
    
    from_rank = chess.square_rank(move.from_square)
    to_rank = chess.square_rank(move.to_square)
    
    # For white, can't decrease rank (moving down)
    if color == chess.WHITE and to_rank < from_rank:
        return False
        
    # For black, can't increase rank (moving down from their perspective)
    if color == chess.BLACK and to_rank > from_rank:
        return False
        
    return True
