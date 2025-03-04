"""
Just Passing Through drawback - can't capture on a specific rank
"""
import chess
from typing import Optional

# Define the drawback properties
DRAWBACK_INFO = {
    "description": "You can't capture on a specific rank",
    "check_move": "check_just_passing_through",
    "supported": True,
    "params": {"rank": 3},  # Configurable rank (0-7)
    "configurable": True,
    "config_type": "rank",
    "config_name": "Restricted Rank"
}

def check_just_passing_through(board: chess.Board, move: chess.Move, color: chess.Color, rank: int = 3) -> bool:
    """Check if a move follows the just passing through rule"""
    assert isinstance(board, chess.Board), "Board must be a chess.Board instance"
    assert isinstance(move, chess.Move), "Move must be a chess.Move instance"
    assert color in [chess.WHITE, chess.BLACK], "Color must be chess.WHITE or chess.BLACK"
    
    # Only check capturing moves
    if not board.is_capture(move):
        return True
        
    # Check the rank of the destination square
    dest_rank = chess.square_rank(move.to_square)
    
    # Adjust for perspective (rank 3 is different for white and black)
    if color == chess.BLACK:
        compare_rank = 7 - rank
    else:
        compare_rank = rank
        
    # Can't capture on the specified rank
    if dest_rank == compare_rank:
        return False
        
    return True
