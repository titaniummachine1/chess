import chess

def illegal_moves(board, color, move):
    """Blocks all bishop moves for the player with this drawback."""
    piece = board.piece_at(move.from_square)
    return piece and piece.piece_type == chess.BISHOP and piece.color == color

def loss_condition(board, color):
    """Example: Player loses if they only have bishops left."""
    return all(board.piece_type_at(sq) == chess.BISHOP for sq in board.occupied_co[color])

drawback_info = {
    "illegal_moves": illegal_moves,
    "loss_condition": loss_condition
}
