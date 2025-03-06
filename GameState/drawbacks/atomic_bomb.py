import chess

# Atomic bomb drawback:
# If your opponent captures a piece adjacent to your king, you lose.
# Kings cannot capture because they would explode.

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
    Check if the player has lost due to an explosion near their king.
    This happens if the last move was a capture adjacent to this player's king.
    """
    assert board is not None, "Board cannot be None"
    assert color in [chess.WHITE, chess.BLACK], f"Invalid color: {color}"
    
    # Don't check during AI search simulations - only on actual board state
    # Skip evaluation during search by checking if we're in a search context
    if hasattr(board, "_in_search") and board._in_search:
        return False
    
    # Only check after a move has been made
    if len(board.move_stack) == 0:
        return False
    
    # Get the last move and see if it was a capture
    last_move = board.move_stack[-1]
    
    # Only trigger when opponent just made a capture
    # Current turn should be the player we're checking for loss,
    # which means the last move was made by the opponent
    if board.turn != color:
        return False
        
    # Check if we have the capture square tracked (this is a safer approach)
    last_capture_square = None
    if hasattr(board, "_last_capture_square") and board._last_capture_square is not None:
        last_capture_square = board._last_capture_square
    else:
        # Fallback: Check if the last move was a capture by checking its flags
        if board.is_capture(last_move):
            last_capture_square = last_move.to_square
    
    # If no capture happened, no explosion
    if last_capture_square is None:
        return False
    
    # Find our king
    king_square = None
    for square, piece in board.piece_map().items():
        if piece and piece.piece_type == chess.KING and piece.color == color:
            king_square = square
            break
    
    # If king not found (already captured), that's a different loss condition
    if king_square is None:
        return False
    
    # Check if the capture square is adjacent to the king
    king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
    capture_file = chess.square_file(last_capture_square)
    capture_rank = chess.square_rank(last_capture_square)
    

    # If the file and rank differences are at most 1, they're adjacent
    if abs(king_file - capture_file) <= 1 and abs(king_rank - capture_rank) <= 1:
        if king_square != last_capture_square:  # Make sure we're not checking the king's own square
            return True  # Loss condition triggered
    
    return False
