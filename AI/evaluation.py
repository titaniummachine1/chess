from enum import Enum
import numpy as np
import chess
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import get_drawback_info

class Score(Enum):
    PAWN = np.int32(100)
    KNIGHT = np.int32(300)
    BISHOP = np.int32(300)
    ROOK = np.int32(500)
    QUEEN = np.int32(900)
    CHECKMATE = np.int32(-1000000)
    MOVE = np.int32(5)

def evaluate(board):
    """Evaluates the board position considering drawbacks."""
    if board.is_variant_loss():
        return Score.CHECKMATE.value  # Player loses if they have no legal moves

    return eval_pieces(board) + eval_moves(board) + eval_positional(board)

def get_piece_value(board, piece_type, color):
    """
    Returns the value of a piece, modified by drawbacks if applicable.
    - If a drawback removes a piece's ability (e.g., "no_knight_moves"), its value becomes 0.
    - Otherwise, it keeps its normal value.
    """
    active_drawback = board.get_active_drawback(color)
    base_values = {
        chess.PAWN: Score.PAWN.value,
        chess.KNIGHT: Score.KNIGHT.value,
        chess.BISHOP: Score.BISHOP.value,
        chess.ROOK: Score.ROOK.value,
        chess.QUEEN: Score.QUEEN.value
    }

    # Get drawback effect
    if active_drawback:
        drawback_info = get_drawback_info(active_drawback)
        if drawback_info and "piece_value_override" in drawback_info:
            return drawback_info["piece_value_override"].get(piece_type, base_values.get(piece_type, 0))

    return base_values.get(piece_type, 0)

def piece_diff(board, piece_type):
    """
    Calculates the material difference of a specific piece type, considering drawback-based value overrides.
    """
    white_count = sum(1 for piece in board.piece_map().values() if piece.color == chess.WHITE and piece.piece_type == piece_type)
    black_count = sum(1 for piece in board.piece_map().values() if piece.color == chess.BLACK and piece.piece_type == piece_type)

    white_value = white_count * get_piece_value(board, piece_type, chess.WHITE)
    black_value = black_count * get_piece_value(board, piece_type, chess.BLACK)

    return np.int32(white_value - black_value if board.turn == chess.WHITE else black_value - white_value)

def eval_pieces(board):
    """Evaluates material balance between White and Black, considering drawbacks."""
    return (piece_diff(board, chess.PAWN)
        + piece_diff(board, chess.KNIGHT)
        + piece_diff(board, chess.BISHOP)
        + piece_diff(board, chess.ROOK)
        + piece_diff(board, chess.QUEEN))

def eval_moves(board):
    """
    Evaluates mobility. More legal moves = better position.
    - If the player has no moves, they lose.
    """
    num_moves = len(list(board.legal_moves))  # Uses drawback-aware move generation

    if num_moves == 0:
        return Score.CHECKMATE.value  # Loss condition

    return Score.MOVE.value * np.int32(num_moves)

def eval_positional(board):
    """
    Evaluates piece placement using default or drawback-modified tables.
    """
    score = 0
    active_drawback = board.get_active_drawback(board.turn)

    for square, piece in board.piece_map().items():
        piece_value = get_piece_value(board, piece.piece_type, piece.color)

        # Skip if piece has 0 value due to drawback
        if piece_value == 0:
            continue

        # Default positional bonus (encourage center control)
        positional_value = 5 if square in [chess.D4, chess.D5, chess.E4, chess.E5] else 0

        # Check if drawback overrides positional values
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "positional_override" in drawback_info:
                override_table = drawback_info["positional_override"].get(piece.piece_type)
                if override_table:
                    positional_value = override_table.get(square, 0)

        # Adjust score based on piece color
        score += positional_value if piece.color == board.turn else -positional_value

    return score
