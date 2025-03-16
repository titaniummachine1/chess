import chess

# Atomic bomb drawback:
# If your opponent captures a piece adjacent to your king, you lose.
# Kings cannot capture because they would explode.

"""
Atomic Bomb Drawback - Pieces cannot be captured adjacent to the king

If a piece is captured adjacent to the king, the player with the atomic_bomb
drawback immediately loses the game.

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

def is_legal(board, move, color):
    """
    Checks if the move is legal under the atomic bomb drawback
    
    Args:
        board: The chess board
        move: The move to check
        color: The color making the move
        
    Returns:
        Boolean indicating if the move is legal
    """
    # If we're in search, we need to allow more moves for proper evaluation
    in_search = getattr(board, "_in_search", False)
    
    # All moves are legal under atomic bomb - the player just loses
    # if a capture is made next to their king
    return True

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
    Check if a capture next to king results in an immediate loss
    for the player with the atomic_bomb drawback.
    
    Args:
        board: Chess board
        color: Color to check (chess.WHITE or chess.BLACK)
        
    Returns:
        Tuple of (has_lost, reason)
    """
    # Get debug flag
    debug_print = not getattr(board, "_in_search", False)
    
    # If we're not in the player's turn, this check doesn't apply
    # A loss condition can only be triggered after opponent moved
    if board.turn != color:
        return False, None
        
    # No moves made - can't lose yet
    if len(board.move_stack) == 0:
        return False, None
        
    # Get the last move - CRITICAL: The loss triggered by opponent's last move
    last_move = board.move_stack[-1]
    
    # Find if the last move was a capture
    was_capture = False
    
    # Try different methods to determine if it was a capture
    if hasattr(board, "_lastmove_was_capture") and board._lastmove_was_capture:
        was_capture = True
    elif hasattr(board, "is_capture") and board.is_capture(last_move):
        was_capture = True
    elif last_move.to_square == board.ep_square:
        was_capture = True
    
    # If last move wasn't a capture, no atomic bomb triggered
    if not was_capture:
        return False, None
    
    # Now check if the capture was adjacent to the player's king
    king_square = None
    
    # Find the king
    for square, piece in board.piece_map().items():
        if piece.piece_type == chess.KING and piece.color == color:
            king_square = square
            break
            
    if king_square is None:
        # King already captured by other means
        return False, None
        
    # Get the capture square (where the last move landed)
    capture_square = last_move.to_square
    
    # Print debug information if needed
    if debug_print:
        print(f"ATOMIC BOMB: Capture detected at {chess.square_name(capture_square)}")
    
    # Check if the capture square is adjacent to the king
    king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
    capture_file = chess.square_file(capture_square)
    capture_rank = chess.square_rank(capture_square)
    
    # Adjacent square = within 1 square in any direction
    is_adjacent = (abs(king_file - capture_file) <= 1 and 
                  abs(king_rank - capture_rank) <= 1 and
                  king_square != capture_square)  # Not the king itself
                  
    if is_adjacent:
        if debug_print:
            print(f"ATOMIC BOMB TRIGGERED: Capture at {chess.square_name(capture_square)} adjacent to king at {chess.square_name(king_square)}")
        return True, "a piece was captured next to their king"
    
    return False, None

def get_description():
    """Returns a description of the drawback"""
    return "If a piece is captured adjacent to your king, you immediately lose the game."

def init_board(board, color):
    """Initialize the board for this drawback"""
    # Store an additional state variable to track if last move was a capture
    board._lastmove_was_capture = False
    # Store the square where the last capture occurred
    board._last_capture_square = None
    
def after_move(board, move, color):
    """Post-move processing for atomic bomb drawback"""
    # Check if the move was a capture and store the result
    was_capture = False
    
    # Handle en passant separately
    if board.piece_at(move.to_square) or move.to_square == board.ep_square:
        was_capture = True
        board._lastmove_was_capture = True
        board._last_capture_square = move.to_square
    else:
        board._lastmove_was_capture = False
        board._last_capture_square = None
    
    # Return normally - loss conditions are checked elsewhere
    return was_capture
