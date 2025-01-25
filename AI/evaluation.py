from enum import Enum
import numpy as np
import chess
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import get_drawback_info

class Score(Enum):
    """Defines piece values and game evaluation constants."""
    PAWN = np.int32(100)
    KNIGHT = np.int32(300)
    BISHOP = np.int32(300)
    ROOK = np.int32(500)
    QUEEN = np.int32(900)
    KING = np.int32(10000)  # High value to make AI prioritize king safety
    CHECKMATE = np.int32(100000)  # Winning state
    MOVE = np.int32(5)  # Mobility bonus

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 10000  # King value is very high because capturing the king ends the game
}

def evaluate_board(board):
    """
    Evaluates the board position.
    """
    if board.is_variant_win():
        return float('inf') if board.turn == chess.WHITE else float('-inf')
    if board.is_variant_loss():
        return float('-inf') if board.turn == chess.WHITE else float('inf')

    material = sum(PIECE_VALUES[piece.piece_type] * (1 if piece.color == chess.WHITE else -1)
                   for piece in board.piece_map().values())
    return material

def evaluate(board):
    """
    Evaluates the board position considering:
    - Piece values (adjusted by drawbacks).
    - King safety (recognizing captures as instant wins).
    - Mobility (more moves = better position).
    - Positional evaluation (encouraging good piece placement).
    """

    # If a king is missing, instantly return win/loss
    white_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.WHITE for piece in board.piece_map().values())
    black_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.BLACK for piece in board.piece_map().values())

    if not black_king_alive:  # White wins by capturing the Black king
        return Score.CHECKMATE.value
    if not white_king_alive:  # Black wins by capturing the White king
        return -Score.CHECKMATE.value

    # If the player has no legal moves, they lose
    if board.is_variant_loss():
        return -Score.CHECKMATE.value

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
        chess.QUEEN: Score.QUEEN.value,
        chess.KING: Score.KING.value  # King should be prioritized
    }

    # Apply drawback modification
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
        + piece_diff(board, chess.QUEEN)
        + piece_diff(board, chess.KING))  # King should be included for proper evaluation

def eval_moves(board):
    """
    Evaluates mobility. More legal moves = better position.
    - If the player has no moves, they lose.
    """
    num_moves = len(list(board.legal_moves))  # Uses drawback-aware move generation

    if num_moves == 0:
        return -Score.CHECKMATE.value  # Losing position

    return Score.MOVE.value * np.int32(num_moves)

def eval_positional(board):
    """
    Evaluates piece placement using default or drawback-modified tables.
    - Encourages control of the center (D4, D5, E4, E5).
    - Applies any drawback-based positional penalties or bonuses.
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
