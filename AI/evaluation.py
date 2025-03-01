from enum import Enum
import numpy as np
import chess
from GameState.drawback_manager import get_drawback_info  # remain for future use
import AI.piece_square_table as pst

# Static material values (pure material, independent of position)
STATIC_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

class Score(Enum):
    PAWN = np.int32(100)
    KNIGHT = np.int32(300)
    BISHOP = np.int32(300)
    ROOK = np.int32(500)
    QUEEN = np.int32(900)
    KING = np.int32(20000)
    CHECKMATE = np.int32(100000)
    MOVE = np.int32(5)

def material_value(piece_type):
    return STATIC_VALUES.get(piece_type, 0)

def get_capture_score(board, attacker, victim):
    """
    Returns a capture bonus using static material values.
    (Attackers lose value when capturing a more valuable piece.)
    """
    # Always allow king capture at highest priority
    if victim.piece_type == chess.KING:
        return 1000000
    return material_value(victim.piece_type) * 10 - material_value(attacker.piece_type)

def get_positional_improvement(board, move):
    """
    Compute bonus as the difference in positional bonus from source to destination.
    For knights, add an extra penalty if moving to the board’s rim.
    """
    piece = board.piece_at(move.from_square)
    if piece is None:
        return 0
    mapping = {
        chess.PAWN: "P",
        chess.KNIGHT: "N",
        chess.BISHOP: "B",
        chess.ROOK: "R",
        chess.QUEEN: "Q",
        chess.KING: "K"
    }
    symbol = mapping.get(piece.piece_type)
    from_val = pst.interpolate_piece_square(symbol, move.from_square, piece.color, board)
    to_val = pst.interpolate_piece_square(symbol, move.to_square, piece.color, board)
    improvement = to_val - from_val
    # Additional penalty for knights moved to the rim
    if piece.piece_type == chess.KNIGHT:
        file = chess.square_file(move.to_square)
        rank = chess.square_rank(move.to_square)
        if file in (0, 7) or rank in (0, 7):
            improvement -= 20  # Adjust penalty as needed
    return improvement

def eval_pieces(board):
    """Material balance using evaluate_board material part."""
    score = 0
    for square, piece in board.piece_map().items():
        base = material_value(piece.piece_type)
        if piece.color == chess.WHITE:
            score += base
        else:
            score -= base
    return score

# The following functions remain similar to before.
def eval_moves(board):
    num_moves = len(list(board.legal_moves))
    if num_moves == 0:
        return -Score.CHECKMATE.value // 2  
    return Score.MOVE.value * np.int32(num_moves)

def eval_king_safety(board):
    safety_score = 0
    offsets = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
    for color in [chess.WHITE, chess.BLACK]:
        king_sq = None
        for square, piece in board.piece_map().items():
            if piece.piece_type == chess.KING and piece.color == color:
                king_sq = square
                break
        if king_sq is None:
            continue
        pawn_cover = 0
        king_file = chess.square_file(king_sq)
        king_rank = chess.square_rank(king_sq)
        for dx, dy in offsets:
            new_file = king_file + dx
            new_rank = king_rank + dy
            if 0 <= new_file < 8 and 0 <= new_rank < 8:
                sq = chess.square(new_file, new_rank)
                neighbor = board.piece_at(sq)
                if neighbor and neighbor.piece_type == chess.PAWN and neighbor.color == color:
                    pawn_cover += 1
        bonus = pawn_cover * 10
        if color == board.turn:
            safety_score += bonus
        else:
            safety_score -= bonus
    return safety_score

def evaluate(board):
    """
    Full evaluation combining piece balance, mobility, king safety,
    and positional bonus from the piece–square tables.
    Material values and positional bonuses are in centipawns.
    """
    # Early termination conditions
    pieces = board.piece_map().values()
    if not any(p.piece_type == chess.KING and p.color == chess.WHITE for p in pieces):
        return Score.CHECKMATE.value
    if not any(p.piece_type == chess.KING and p.color == chess.BLACK for p in pieces):
        return -Score.CHECKMATE.value
    if board.is_variant_loss():
        return -Score.CHECKMATE.value

    material = eval_pieces(board)
    mobility = eval_moves(board)
    safety = eval_king_safety(board)
    
    positional = 0
    mapping = {
        chess.PAWN: "P",
        chess.KNIGHT: "N",
        chess.BISHOP: "B",
        chess.ROOK: "R",
        chess.QUEEN: "Q",
        chess.KING: "K"
    }
    # Sum positional bonus over all pieces.
    for square, piece in board.piece_map().items():
        pos_bonus = pst.interpolate_piece_square(mapping[piece.piece_type], square, piece.color, board)
        positional += pos_bonus if piece.color == chess.WHITE else -pos_bonus

    # Remove the 0.5 weight to add full piece-square bonus.
    return material + mobility + safety + positional

# Fallback transposition key helper for search use.
def get_transposition_key(board):
    # For now, simply return the board FEN.
    # Replace with a proper Zobrist hash if needed.
    return board.fen()
