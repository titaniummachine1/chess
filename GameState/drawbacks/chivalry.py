"""
Chivalry drawback - only knights can capture rooks and queens
"""
import chess
from typing import Optional

# Define the drawback properties
DRAWBACK_INFO = {
    "description": "You can only capture rooks and queens with knights",
    "check_move": "check_chivalry",
    "supported": True
}

def check_chivalry(board: chess.Board, move: chess.Move, color: chess.Color) -> bool:
    """Check if a move follows the chivalry rule"""
    assert isinstance(board, chess.Board), "Board must be a chess.Board instance"
    assert isinstance(move, chess.Move), "Move must be a chess.Move instance"
    assert color in [chess.WHITE, chess.BLACK], "Color must be chess.WHITE or chess.BLACK"
    
    # Only check capturing moves
    if not board.is_capture(move):
        return True
        
    # Get pieces involved
    moving_piece = board.piece_at(move.from_square)
    target_piece = board.piece_at(move.to_square)
    
    # Only knights can capture rooks and queens
    if target_piece and (target_piece.piece_type == chess.ROOK or target_piece.piece_type == chess.QUEEN):
        if not moving_piece or moving_piece.piece_type != chess.KNIGHT:
            return False
            
    return True
