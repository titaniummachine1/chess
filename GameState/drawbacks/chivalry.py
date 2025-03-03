"""
Chivalry drawback - only knights can capture rooks and queens
"""
import chess

def check_chivalry(board, move, color):
    """Check if a move follows the chivalry rule"""
    
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
