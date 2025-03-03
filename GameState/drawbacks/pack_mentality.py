"""
Pack Mentality drawback: Your pieces must move to squares adjacent to another one of your pieces.
"""
import chess

DRAWBACK_INFO = {
    "name": "Pack Mentality",
    "description": "Your pieces must move to squares adjacent to another one of your pieces",
    "check_move": "check_pack_mentality",
    "supported": True
}

def check_pack_mentality(board, move, color):
    """Check if a move follows the pack mentality rule"""
    
    # Make a copy of the board and apply the move
    board_copy = board.copy()
    
    # Get the destination square
    dest_square = move.to_square
    
    # Get the moving piece
    moving_piece = board.piece_at(move.from_square)
    if not moving_piece:
        return False
    
    # Apply the move to check the resulting position
    board_copy.push(move)
    
    # Check all adjacent squares to see if any contain a friendly piece
    file = chess.square_file(dest_square)
    rank = chess.square_rank(dest_square)
    
    # Check all 8 adjacent squares
    for f_offset in [-1, 0, 1]:
        for r_offset in [-1, 0, 1]:
            # Skip the center square (the piece's destination)
            if f_offset == 0 and r_offset == 0:
                continue
                
            # Calculate adjacent square
            adj_file = file + f_offset
            adj_rank = rank + r_offset
            
            # Check if square is on the board
            if 0 <= adj_file < 8 and 0 <= adj_rank < 8:
                adj_square = chess.square(adj_file, adj_rank)
                
                # Check if adjacent square has a friendly piece
                adj_piece = board_copy.piece_at(adj_square)
                if adj_piece and adj_piece.color == color and adj_square != move.from_square:
                    return True  # Found a friendly piece adjacent to destination
    
    # No adjacent friendly pieces found
    return False
