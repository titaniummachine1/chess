import chess

def illegal_moves(board, color, move):
    print(f"illegal_moves called with board: {board}, color: {color}, move: {move}")
    piece = board.piece_at(move.from_square)
    if piece:
        print(f"Piece at move.from_square: {piece}")
    if piece and piece.color == color and piece.piece_type == chess.KNIGHT:
        print(f"Blocking Knight move: {move}")
        return True
    return False

DRAWBACK_INFO = {
    "name": "No Knight Moves",
    "illegal_moves": illegal_moves,
    "loss_condition": None,
    "piece_value_override": {
        chess.KNIGHT: 0
    }
}
