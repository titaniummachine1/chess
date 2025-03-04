import chess

# Atomic bomb drawback:
# If your opponent captures a piece adjacent to your king, you lose.
# Kings cannot capture because they would explode.

DRAWBACK_INFO = {
    "name": "Atomic Bomb",
    "description": "If your opponent captures a piece adjacent to your king, you lose",
    "check_move": "check_atomic_bomb",
    "supported": True,
    "loss_condition": "check_explosion_loss"
}

def check_atomic_bomb(board, move, color):
    """
    Check if a move is legal according to Atomic Bomb drawback:
    - Kings cannot capture pieces (they would explode)
    """
    # Get the piece that's moving
    piece = board.piece_at(move.from_square)
    
    # Kings cannot capture pieces (they would explode)
    if piece and piece.piece_type == chess.KING and board.is_capture(move):
        return True  # Return True to indicate this move is ILLEGAL
        
    # All other moves are allowed
    return False  # Return False to indicate this move is LEGAL
    
def check_explosion_loss(board, color):
    """
    Check if the player has lost due to an explosion near their king.
    This happens if the last move was a capture adjacent to this player's king.
    """
    # Only check after a move has been made
    if len(board.move_stack) == 0:
        return False
        
    last_move = board.move_stack[-1]
    
    # If it wasn't a capture, no explosion
    if not board.is_capture(last_move):
        return False
    
    # Find the king's position for the current player
    king_square = None
    for square, piece in board.piece_map().items():
        if piece.piece_type == chess.KING and piece.color == color:
            king_square = square
            break
    
    # If king not found (already captured), that's a different loss condition
    if king_square is None:
        return False
        
    # Check if the capture was adjacent to the king
    capture_square = last_move.to_square
    
    # Get all squares around the king
    king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
    adjacent_squares = []
    
    # Generate all adjacent squares
    for f_offset in [-1, 0, 1]:
        for r_offset in [-1, 0, 1]:
            if f_offset == 0 and r_offset == 0:
                continue  # Skip the king's own square
            
            adj_file = king_file + f_offset
            adj_rank = king_rank + r_offset
            
            # Check if the adjacent square is within the board
            if 0 <= adj_file < 8 and 0 <= adj_rank < 8:
                adj_square = chess.square(adj_file, adj_rank)
                adjacent_squares.append(adj_square)
    
    # If the capture happened on an adjacent square, the king exploded
    return capture_square in adjacent_squares
