"""
Chivalry drawback - only knights can capture rooks and queens
"""
import chess
from typing import Optional

# Chivalry drawback:
# You can't capture pieces directly with your knights or king.
# Knights and kings may only move to empty squares.

DRAWBACK_INFO = {
    "name": "Chivalry",
    "description": "Your knights and king may not capture any pieces. They must move to empty squares only.",
    "check_move": "check_chivalry",  # Function reference as a string
    "supported": True
}

def check_chivalry(board: chess.Board, move: chess.Move, color: chess.Color) -> bool:
    """Check if a move follows the chivalry rule"""
    assert isinstance(board, chess.Board), "Board must be a chess.Board instance"
    assert isinstance(move, chess.Move), "Move must be a chess.Move instance"
    assert color in [chess.WHITE, chess.BLACK], "Color must be chess.WHITE or chess.BLACK"
    
    # Get the piece that's moving
    piece = board.piece_at(move.from_square)
    
    # If no piece found, move is valid (this shouldn't happen)
    if not piece:
        return False  # Not illegal
        
    # Check if this is a king or knight
    if piece.piece_type in [chess.KING, chess.KNIGHT]:
        # Check if destination square has a piece (capture)
        if board.piece_at(move.to_square) is not None:
            return True  # The move is illegal (cannot capture)
    
    # All other moves are allowed
    return False  # Not illegal
