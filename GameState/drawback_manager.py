import chess

def check_drawback(board, move, drawback):
    """Check if a move is allowed under the player's current drawback."""
    if not drawback:
        return True  # No drawback, all moves allowed

    if drawback == "no_bishop_captures" and board.piece_at(move.from_square).piece_type == chess.BISHOP:
        return not board.is_capture(move)  # Bishops cannot capture

    if drawback == "only_knight_moves" and board.piece_at(move.from_square).piece_type != chess.KNIGHT:
        return False  # Player can only move knights

    if drawback == "king_must_move" and board.piece_at(move.from_square).piece_type != chess.KING:
        return False  # Player must move their king

    if drawback == "rook_cannot_move_twice":
        history = [m for m in board.move_stack if board.piece_at(m.from_square).piece_type == chess.ROOK]
        if history and board.piece_at(move.from_square).piece_type == chess.ROOK:
            return False  # Rooks cannot move twice

    return True  # Default: move is allowed

def check_drawback_loss(board, color=None):
    """Check if a player loses due to a drawback condition."""
    if color is None:
        color = board.turn  # Check current player by default

    drawback = board.get_drawback(color)

    if drawback == "must_checkmate_in_10" and board.fullmove_number > 10:
        return True  # Player loses if they haven't checkmated in 10 moves

    if drawback == "cannot_move_pieces":
        return all(
            board.piece_at(sq) is None or board.piece_at(sq).color != color
            for sq in chess.SQUARES
        )  # Player loses if they cannot move any pieces

    return False  # Default: player does not lose
