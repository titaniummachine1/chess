"""
Blinded by the Sun drawback - can't end turn attacking the sun square
"""
import chess

def check_blinded_by_the_sun(board, move, color, sun_square=chess.E4):
    """Check if a move follows the blinded by the sun rule"""
    
    # Make a copy of the board and apply the move
    board_copy = board.copy()
    board_copy.push(move)
    
    # Check if the moving player is attacking the sun square after the move
    if board_copy.is_attacked_by(color, sun_square):
        return False  # Can't end turn attacking sun square
        
    return True
