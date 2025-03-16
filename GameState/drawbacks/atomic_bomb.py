import chess

# Atomic bomb drawback:
# If your opponent captures a piece adjacent to your king, you lose.
# Kings cannot capture because they would explode.

"""
Drawback: Atomic Bomb
Description: If your opponent captures a piece adjacent to your king, you lose.

Reverse Imports:
- AI/engine_core.py: imports check_explosion_loss for loss condition check
- main.py: checks for this drawback in check_game_end_conditions
- AI/search_utils.py: special case handling for atomic bomb
- AI/drawback_Bot.py: special evaluation handling
- AI/drawback_sunfish.py: special case handling
"""

DRAWBACK_INFO = {
    "name": "Atomic Bomb",
    "description": "If your opponent captures a piece adjacent to your king, you lose",
    "check_move": "check_atomic_bomb",
    "loss_condition": "check_explosion_loss",
    "supported": True
}

def check_atomic_bomb(board, move, color):
    """
    Check if a move is legal according to Atomic Bomb drawback:
    - Kings cannot capture pieces (they would explode)
    """
    assert board is not None, "Board cannot be None"
    assert move is not None, "Move cannot be None"
    assert color in [chess.WHITE, chess.BLACK], f"Invalid color: {color}"
    
    # Get the piece that's moving
    piece = board.piece_at(move.from_square)
    
    # Kings cannot capture pieces (they would explode)
    if piece and piece.piece_type == chess.KING:
        # Direct check for target piece without using is_capture
        target = board.piece_at(move.to_square)
        if target:  # There's a piece at the destination = capture
            return True  # This move is ILLEGAL
        
    # All other moves are allowed
    return False

def check_explosion_loss(board, color):
    """
    Check if a player has lost due to a piece being captured adjacent to their king.
    
    Args:
        board: The current chess board
        color: The color to check for loss (the player with the atomic_bomb drawback)
    
    Returns:
        tuple: (has_lost, reason) where has_lost is a boolean and reason is a string
    """
    # Safety check 1: Ensure there was at least one move
    if len(board.move_stack) == 0:
        print("ATOMIC: No moves made yet, cannot have atomic explosion")
        return False, None
    
    # Safety check 2: It must be the affected player's turn
    # This means the opponent just moved and potentially made a capture
    if board.turn != color:
        print(f"ATOMIC: Not {color}'s turn, so opponent didn't just move")
        return False, None
    
    # Safety check 3: The last move must be a capture
    # Use the DrawbackBoard's tracking properties directly
    was_capture = False
    
    # Check if board has a tracking flag (which DrawbackBoard does)
    if hasattr(board, '_lastmove_was_capture'):
        was_capture = board._lastmove_was_capture
        if was_capture:
            print("ATOMIC: Board history indicates a capture")
    
    # Final safety check
    if not was_capture:
        print(f"ATOMIC: Last move was not a capture")
        return False, None
    
    # Find the king of the player with atomic bomb drawback
    king_square = None
    for square, piece in board.piece_map().items():
        if piece.piece_type == chess.KING and piece.color == color:
            king_square = square
            break
    
    if king_square is None:
        # King already captured through normal means
        return False, None
    
    # Get the capture square from the board's tracking
    capture_square = None
    if hasattr(board, '_last_capture_square'):
        capture_square = board._last_capture_square
    
    # If no capture square information, can't determine adjacency
    if capture_square is None:
        print("ATOMIC: No capture square information available")
        return False, None
    
    print(f"DEBUG: Last capture at {chess.square_name(capture_square)}")
    
    # Check if the capture was adjacent to the king
    king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
    capture_file, capture_rank = chess.square_file(capture_square), chess.square_rank(capture_square)
    
    # Adjacent if file and rank differ by at most 1
    is_adjacent = (abs(king_file - capture_file) <= 1 and 
                   abs(king_rank - capture_rank) <= 1)
    
    if is_adjacent:
        print(f"ATOMIC: Player {color} lost due to a capture at {chess.square_name(capture_square)} " 
              f"adjacent to their king at {chess.square_name(king_square)}")
        return True, f"{'White' if color == chess.WHITE else 'Black'} lost - a piece was captured next to their king"
    
    print(f"ATOMIC: Capture at {chess.square_name(capture_square)} was not adjacent to king at {chess.square_name(king_square)}")
    return False, None
