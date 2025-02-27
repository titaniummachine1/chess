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
    KING = np.int32(20000)  # Extremely high value to make king capture an absolute priority
    CHECKMATE = np.int32(100000)  # Winning state
    MOVE = np.int32(5)  # Mobility bonus

# Standard piece values
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000  # Making king worth much more to prioritize its capture
}

def evaluate_board(board):
    """
    Evaluates the board position based on material and drawbacks.
    """
    # Check for king capture (immediate win/loss situation)
    white_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.WHITE 
                          for piece in board.piece_map().values())
    black_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.BLACK 
                          for piece in board.piece_map().values())
    
    if not black_king_alive:
        return float('inf')  # White wins by capturing the Black king
    if not white_king_alive:
        return float('-inf')  # Black wins by capturing the White king

    # Continue with normal evaluation if both kings are alive
    material = 0
    
    # Calculate material for each piece, taking drawbacks into account
    for square, piece in board.piece_map().items():
        value = get_piece_value(board, piece.piece_type, piece.color)
        if piece.color == chess.WHITE:
            material += value
        else:
            material -= value
            
    # Adjust for whose turn it is
    if board.turn == chess.BLACK:
        material = -material
        
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
        return Score.CHECKMATE.value  # Maximum positive score
    if not white_king_alive:  # Black wins by capturing the White king
        return -Score.CHECKMATE.value  # Maximum negative score

    # If the player has no legal moves, they lose
    if board.is_variant_loss():
        return -Score.CHECKMATE.value

    return eval_pieces(board) + eval_moves(board) + eval_positional(board) + eval_drawback_specific(board)

def get_piece_value(board, piece_type, color):
    """
    Returns the value of a piece, modified by drawbacks if applicable.
    - If a drawback affects a piece's value, use the drawback's override
    - Otherwise, use the standard value
    """
    active_drawback = board.get_active_drawback(color)
    base_values = PIECE_VALUES.copy()

    # Special case for kings - always keep them valuable
    if piece_type == chess.KING:
        return base_values[chess.KING]

    # Apply drawback modification for other pieces
    if active_drawback:
        drawback_info = get_drawback_info(active_drawback)
        if drawback_info and "piece_value_override" in drawback_info:
            override_value = drawback_info["piece_value_override"].get(piece_type)
            if override_value is not None:
                return override_value

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
    - If the player has no moves and the king is in danger, they're likely to lose soon
    """
    num_moves = len(list(board.legal_moves))  # Uses drawback-aware move generation

    if num_moves == 0:
        # In Drawback Chess, having no moves isn't an immediate loss,
        # but it's still very bad
        return -Score.CHECKMATE.value // 2  

    return Score.MOVE.value * np.int32(num_moves)

def eval_positional(board):
    """
    Evaluates piece placement using default or drawback-modified tables.
    - Encourages control of the center (D4, D5, E4, E5).
    - Applies any drawback-based positional penalties or bonuses.
    """
    score = 0
    active_drawback = board.get_active_drawback(board.turn)

    # Center control bonus
    central_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
    
    for square, piece in board.piece_map().items():
        piece_value = get_piece_value(board, piece.piece_type, piece.color)

        # Skip if piece has 0 value due to drawback
        if piece_value == 0:
            continue

        # Default positional bonus (encourage center control)
        positional_value = 5 if square in central_squares else 0

        # Adjust score based on piece color
        score += positional_value if piece.color == board.turn else -positional_value

    return score

def eval_drawback_specific(board):
    """
    Apply specific evaluation bonuses/penalties based on the active drawbacks.
    """
    score = 0
    
    # Get drawbacks for both players
    white_drawback = board.get_active_drawback(chess.WHITE)
    black_drawback = board.get_active_drawback(chess.BLACK)
    
    # Check for strategic advantages based on drawbacks
    if board.turn == chess.WHITE:
        # White is playing
        
        # If White has no knight moves, encourage pawn advancement and bishop development
        if white_drawback == "no_knight_moves":
            # Count advanced pawns and developed bishops
            for square, piece in board.piece_map().items():
                if piece.color == chess.WHITE:
                    rank = chess.square_rank(square)
                    if piece.piece_type == chess.PAWN and rank >= 3:  # Pawn advanced to rank 4 or beyond
                        score += 5
                    elif piece.piece_type == chess.BISHOP and rank >= 2:  # Bishop developed
                        score += 10
        
        # If White has punching down restriction, prioritize protecting valuable pieces
        elif white_drawback == "punching_down":
            # Bonus for having pawns near valuable pieces
            for square, piece in board.piece_map().items():
                if piece.color == chess.WHITE and piece.piece_type in [chess.QUEEN, chess.ROOK]:
                    # Check for pawn protection
                    piece_rank = chess.square_rank(square)
                    piece_file = chess.square_file(square)
                    # Look for pawns that can protect this piece
                    for pawn_offset in [(-1, -1), (-1, 1)]:  # Diagonal squares a pawn would defend from
                        pr, pf = piece_rank + pawn_offset[0], piece_file + pawn_offset[1]
                        if 0 <= pr < 8 and 0 <= pf < 8:
                            pawn_sq = chess.square(pf, pr)
                            pawn = board.piece_at(pawn_sq)
                            if pawn and pawn.piece_type == chess.PAWN and pawn.color == chess.WHITE:
                                score += 15  # Bonus for having a pawn protecting valuable piece
        
        # If Black can't capture with knights or bishops, that's an advantage for White
        if black_drawback in ["no_knight_captures", "no_bishop_captures"]:
            score += 15  # Generic bonus for opponent's capture restriction
            
        # If Black has "punching down", White should prioritize exposing their queen
        if black_drawback == "punching_down":
            # Look for opportunities to attack with queen
            for square, piece in board.piece_map().items():
                if piece.color == chess.WHITE and piece.piece_type == chess.QUEEN:
                    # Bonus for queen mobility - number of squares it can move to
                    queen_mobility = sum(1 for move in board.legal_moves 
                                         if move.from_square == square)
                    score += queen_mobility * 2  # Each mobility square is worth 2 points
            
    else:
        # Black is playing
        
        # If Black has no knight moves, encourage pawn advancement and bishop development
        if black_drawback == "no_knight_moves":
            # Count advanced pawns and developed bishops
            for square, piece in board.piece_map().items():
                if piece.color == chess.BLACK:
                    rank = chess.square_rank(square)
                    if piece.piece_type == chess.PAWN and rank <= 4:  # Pawn advanced to rank 5 or beyond
                        score += 5
                    elif piece.piece_type == chess.BISHOP and rank <= 5:  # Bishop developed
                        score += 10
        
        # If Black has punching down restriction, prioritize protecting valuable pieces
        elif black_drawback == "punching_down":
            # Bonus for having pawns near valuable pieces
            for square, piece in board.piece_map().items():
                if piece.color == chess.BLACK and piece.piece_type in [chess.QUEEN, chess.ROOK]:
                    # Check for pawn protection
                    piece_rank = chess.square_rank(square)
                    piece_file = chess.square_file(square)
                    # Look for pawns that can protect this piece
                    for pawn_offset in [(1, -1), (1, 1)]:  # Diagonal squares a pawn would defend from
                        pr, pf = piece_rank + pawn_offset[0], piece_file + pawn_offset[1]
                        if 0 <= pr < 8 and 0 <= pf < 8:
                            pawn_sq = chess.square(pf, pr)
                            pawn = board.piece_at(pawn_sq)
                            if pawn and pawn.piece_type == chess.PAWN and pawn.color == chess.BLACK:
                                score += 15  # Bonus for having a pawn protecting valuable piece
        
        # If White can't capture with knights or bishops, that's an advantage for Black
        if white_drawback in ["no_knight_captures", "no_bishop_captures"]:
            score += 15  # Generic bonus for opponent's capture restriction
        
        # If White has "punching down", Black should prioritize exposing their queen
        if white_drawback == "punching_down":
            # Look for opportunities to attack with queen
            for square, piece in board.piece_map().items():
                if piece.color == chess.BLACK and piece.piece_type == chess.QUEEN:
                    # Bonus for queen mobility - number of squares it can move to
                    queen_mobility = sum(1 for move in board.legal_moves 
                                         if move.from_square == square)
                    score += queen_mobility * 2  # Each mobility square is worth 2 points
    
    return score
