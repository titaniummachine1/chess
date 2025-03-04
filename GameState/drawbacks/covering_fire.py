"""
Covering Fire drawback - Can only capture if you could capture the piece in two different ways
"""
import chess

# Define the drawback properties
DRAWBACK_INFO = {
    "description": "You can only capture a piece if you could capture it two different ways",
    "check_move": "check_covering_fire",
    "supported": True
}

def check_covering_fire(board, move, color):
    """
    Check if a move complies with the covering fire rule:
    - Can only capture if the piece can be captured by at least two different pieces
    """
    # If it's not a capture, allow the move
    if not board.is_capture(move):
        return True
        
    # For captures, check if another piece can also capture the target
    target_square = move.to_square
    attacking_count = 0
    
    # Count how many pieces of the player's color attack the target square
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        
        # Check if this square contains a piece of the player's color
        if piece and piece.color == color:
            # Create a move from this square to the target square
            if square != move.from_square:  # Skip the piece that's making the actual move
                # Check if this move would be a valid capture
                try:
                    potential_move = chess.Move(square, target_square)
                    if board.is_pseudo_legal(potential_move) and potential_move != move:
                        attacking_count += 1
                        # If we have at least one other attacker, the move is allowed
                        if attacking_count >= 1:
                            return True
                except Exception:
                    # Skip invalid moves
                    continue
    
    # If we didn't find at least one other attacker, the move is not allowed
    return False
