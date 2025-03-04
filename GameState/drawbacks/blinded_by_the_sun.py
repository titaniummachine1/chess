"""
Blinded by the Sun drawback - can't end turn attacking the sun square
"""
import chess
from typing import Optional

# Define the drawback properties
DRAWBACK_INFO = {
    "description": "You can't end your turn attacking a specific square",
    "check_move": "check_blinded_by_the_sun",
    "supported": True,
    "params": {"sun_square": chess.E4},
    "configurable": True,
    "config_type": "square",
    "config_name": "Sun Square"
}

def check_blinded_by_the_sun(board: chess.Board, move: chess.Move, color: chess.Color, sun_square: int = chess.E4) -> bool:
    """Check if a move follows the blinded by the sun rule"""
    assert isinstance(board, chess.Board), "Board must be a chess.Board instance"
    assert isinstance(move, chess.Move), "Move must be a chess.Move instance"
    assert color in [chess.WHITE, chess.BLACK], "Color must be chess.WHITE or chess.BLACK"
    
    # Make a copy of the board and apply the move
    board_copy = board.copy()
    board_copy.push(move)
    
    # Check if the moving player is attacking the sun square after the move
    if board_copy.is_attacked_by(color, sun_square):
        return False  # Can't end turn attacking sun square
        
    return True
