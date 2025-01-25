# GameState/drawbacks/no_knight_moves.py

import chess

def illegal_moves(board, color, move):
    """
    Blocks knight moves for the given player.
    """
    piece = board.piece_at(move.from_square)
    
    # If the piece is a knight and belongs to the current player, restrict it
    return piece is not None and piece.color == color and piece.piece_type == chess.KNIGHT

DRAWBACK_INFO = {
    "name": "No Knight Moves",
    "illegal_moves": illegal_moves,
    "loss_condition": None,  # No immediate loss condition
    "piece_value_override": {
        chess.KNIGHT: 0  # Knights are useless
    }
}
