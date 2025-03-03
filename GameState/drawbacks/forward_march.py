"""
Forward March drawback - can't move backwards
"""
import chess

def check_forward_march(board, move, color):
    """Check if a move follows the forward march rule"""
    
    from_rank = chess.square_rank(move.from_square)
    to_rank = chess.square_rank(move.to_square)
    
    # For white, can't decrease rank (moving down)
    if color == chess.WHITE and to_rank < from_rank:
        return False
        
    # For black, can't increase rank (moving down from their perspective)
    if color == chess.BLACK and to_rank > from_rank:
        return False
        
    return True
