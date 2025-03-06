"""
Template Drawback - Use this as a reference for creating new drawbacks
"""
import chess

DRAWBACK_INFO = {
    "name": "Template Drawback",
    "description": "Description of what this drawback does",
    "check_move": "check_template_move",      # Name of move checking function
    "loss_condition": "check_template_loss",  # Optional loss condition function (can be omitted)
    "supported": True                         # Set to True when fully implemented
}

def check_template_move(board, move, color):
    """
    Check if a move is legal according to this drawback.
    
    Args:
        board: The current board state (DrawbackBoard)
        move: The chess.Move to check
        color: The color making the move (chess.WHITE or chess.BLACK)
        
    Returns:
        True if the move is ILLEGAL (not allowed)
        False if the move is legal (allowed)
    """
    # IMPORTANT: Return True if the move is ILLEGAL (not allowed by the drawback)
    # Return False if the move is legal (allowed by the drawback)
    
    # Example implementation:
    # Get the piece that's moving
    piece = board.piece_at(move.from_square)
    
    # If no piece found or wrong color, something's wrong
    if not piece or piece.color != color:
        return False  # Move is legal (this shouldn't happen)
    
    # Example: Bishops can't capture pawns
    if piece.piece_type == chess.BISHOP:
        target = board.piece_at(move.to_square)
        if target and target.piece_type == chess.PAWN:
            return True  # This move is ILLEGAL
    
    # All other moves are legal
    return False


def check_template_loss(board, color):
    """
    Check if the player has lost due to this drawback's special condition.
    
    Args:
        board: The current board state (DrawbackBoard)
        color: The color to check for loss (chess.WHITE or chess.BLACK)
        
    Returns:
        True if the loss condition is met (player loses)
        False if no loss condition is triggered
    """
    # IMPORTANT: Return True if the player has lost
    # Return False if no loss condition is triggered
    
    # Example implementation:
    # Check if the player has no knights left
    has_knights = False
    for square, piece in board.piece_map().items():
        if piece and piece.color == color and piece.piece_type == chess.KNIGHT:
            has_knights = True
            break
    
    # In this example, player loses if they have no knights
    if not has_knights:
        return True  # Player has lost
    
    # No loss condition triggered
    return False 