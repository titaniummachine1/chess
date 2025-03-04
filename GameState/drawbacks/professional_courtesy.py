"""
Professional Courtesy drawback - can't capture non-pawn pieces with pieces of the same type
"""
import chess
from typing import Optional

# Define the drawback properties
DRAWBACK_INFO = {
    "description": "You can't capture non-pawn pieces with pieces of the same type",
    "check_move": "check_professional_courtesy",
    "supported": True
}

def check_professional_courtesy(board: chess.Board, move: chess.Move, color: chess.Color) -> bool:
    """Check if a move follows the professional courtesy rule"""
    assert isinstance(board, chess.Board), "Board must be a chess.Board instance"
    assert isinstance(move, chess.Move), "Move must be a chess.Move instance"
    assert color in [chess.WHITE, chess.BLACK], "Color must be chess.WHITE or chess.BLACK"
    
    # Only check capturing moves
    if not board.is_capture(move):
        return True
        
    # Get pieces involved
    moving_piece = board.piece_at(move.from_square)
    target_piece = board.piece_at(move.to_square)
    
    # If either piece is null, something is wrong
    if not moving_piece or not target_piece:
        return True
    
    # Professional courtesy applies only to non-pawn pieces
    if target_piece.piece_type != chess.PAWN:
        # Can't capture if same piece type (professional courtesy)
        if moving_piece.piece_type == target_piece.piece_type:
            return False
    
    return True
