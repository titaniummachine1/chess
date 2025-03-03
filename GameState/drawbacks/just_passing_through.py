"""
Just Passing Through drawback - can't capture on a specific rank
"""
import chess

def check_just_passing_through(board, move, color, rank=3):
    """Check if a move follows the just passing through rule"""
    
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
